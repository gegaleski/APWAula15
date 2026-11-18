from rest_framework import serializers
from django.db import transaction

from .models import (
    Produto,
    Categoria,
    Cliente,
    Pedido,
    ItemPedido
)

from django.contrib.auth.models import User
from rest_framework import serializers
from .models import Cliente



# Classe usuarioserializer

class CadastroUsuarioSerializers(serializers.Serializer):

    username = serializers.CharField()
    password = serializers.CharField(write_only = True)

    nome = serializers.CharField()
    email = serializers.EmailField()
    telefone = serializers.CharField(
        required = False,
        allow_blank = True
    )

    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("Este nome de usuário já está cadastrado")
        return value

    def validate_email(self, value):

        if Cliente.objects.filter(email__iexact=value).exists() or User.objects.filter(email__iexact=value).exists():

            raise serializers.ValidationError("Este email já está cadastrado")
        return value

    @transaction.atomic
    def create(self, validated_data):

        #Cria o usuario de autenticação do Django

        usuario = User.objects.create_user(
            username = validated_data['username'],
            email = validated_data['email'],
            password = validated_data['password']
        )


        # cria o cliente

        cliente = Cliente.objects.create(
            usuario =usuario,
            nome = validated_data['nome'],
            email = validated_data['email'],
            telefone = validated_data.get('telefone','')
        )

        return cliente

    def to_representation(self, instance):

        return{
            "id": instance.id,
            "username":instance.usuario.username,
            "nome":instance.nome,
            "email":instance.email,
            "telefone":instance.telefone
        }


# Categoria
class CategoriaSerializer(serializers.ModelSerializer):

    class Meta:
        model = Categoria
        fields = "__all__"


# Produto
class ProdutoSerializer(serializers.ModelSerializer):

    class Meta:
        model = Produto
        fields = "__all__"


# Cliente
class ClienteSerializer(serializers.ModelSerializer):

    class Meta:
        model = Cliente
        fields = "__all__"


# ItemPedido
class ItemPedidoSerializer(serializers.ModelSerializer):

    subtotal = serializers.SerializerMethodField(
        read_only=True
    )

    class Meta:
        model = ItemPedido

        fields = [
            "id",
            "pedido",
            "produto",
            "quantidade",
            "preco_unitario",
            "subtotal"
        ]

        read_only_fields = [
            "preco_unitario"
        ]

    def get_subtotal(self, obj):
        return obj.subtotal()

class ProdutoPorNomeField(serializers.RelatedField):
    """Aceita o nome do produto no POST e devolve o nome no GET."""

    def to_internal_value(self, data):
        if not isinstance(data, str) or not data.strip():
            raise serializers.ValidationError("Informe o nome do produto.")
        produtos = Produto.objects.filter(nome__iexact=data.strip())
        if not produtos.exists():
            raise serializers.ValidationError(f"Produto '{data}' não encontrado.")
        if produtos.count() > 1:
            raise serializers.ValidationError(
                f"Há mais de um produto chamado '{data}'. Renomeie os produtos duplicados."
            )
        return produtos.first()

    def to_representation(self, value):
        return value.nome


class ItemPedidoDetalheSerializer(serializers.ModelSerializer):

    produto = ProdutoPorNomeField(queryset=Produto.objects.all())

    produto_nome = serializers.CharField(
        source="produto.nome",
        read_only=True
    )

    subtotal = serializers.SerializerMethodField(
        read_only=True
    )

    class Meta:
        model = ItemPedido

        fields = [
            "id",
            "produto",
            "produto_nome",
            "quantidade",
            "preco_unitario",
            "subtotal"
        ]

    def get_subtotal(self, obj):
        return obj.subtotal()


# Pedido: aceita JSON simples (produto, quantidade, cliente) ou lista de itens.
class PedidoSerializer(serializers.ModelSerializer):
    cliente = serializers.CharField(required=False)
    produto = ProdutoPorNomeField(queryset=Produto.objects.all(), write_only=True, required=False)
    quantidade = serializers.IntegerField(min_value=1, write_only=True, required=False)
    itens = ItemPedidoDetalheSerializer(many=True, required=False)
    total = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Pedido
        fields = [
            "id", "cliente", "produto", "quantidade", "descricao",
            "data_pedido", "status", "itens", "total"
        ]
        read_only_fields = ["id", "data_pedido", "status", "total"]

    def to_representation(self, instance):
        resultado = super().to_representation(instance)
        resultado["cliente"] = instance.cliente.nome
        return resultado

    def validate(self, attrs):
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            try:
                cliente_autenticado = Cliente.objects.get(usuario=request.user)
            except Cliente.DoesNotExist:
                raise serializers.ValidationError(
                    {"cliente": "Usuário autenticado não possui cadastro de cliente."}
                )
            nome_cliente = attrs.pop("cliente", None)
            if nome_cliente is not None and nome_cliente.strip().casefold() != cliente_autenticado.nome.strip().casefold():
                raise serializers.ValidationError(
                    {"cliente": "Informe o nome do cliente associado ao usuário autenticado."}
                )

        produto = attrs.pop("produto", None)
        quantidade = attrs.pop("quantidade", None)
        itens = attrs.get("itens")
        if produto is not None or quantidade is not None:
            if itens is not None:
                raise serializers.ValidationError(
                    "Envie produto e quantidade OU a lista itens, não os dois formatos."
                )
            if produto is None or quantidade is None:
                raise serializers.ValidationError(
                    "Informe produto e quantidade no pedido."
                )
            attrs["itens"] = [{"produto": produto, "quantidade": quantidade}]
        elif not itens:
            raise serializers.ValidationError("Informe produto e quantidade, ou uma lista de itens.")

        for item in attrs["itens"]:
            if item["quantidade"] <= 0:
                raise serializers.ValidationError("A quantidade deve ser maior que zero.")
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        itens_data = validated_data.pop("itens")
        pedido = Pedido.objects.create(**validated_data)
        for item_data in itens_data:
            ItemPedido.objects.create(pedido=pedido, **item_data)
        return pedido

    def get_total(self, obj):
        return obj.total()

# Alteração do status do pedido
class StatusPedidoSerializer(serializers.ModelSerializer):

    itens = ItemPedidoDetalheSerializer(
        many=True,
        read_only=True
    )

    total = serializers.SerializerMethodField(
        read_only=True
    )

    class Meta:
        model = Pedido

        fields = [
            "id",
            "cliente",
            "descricao",
            "data_pedido",
            "status",
            "itens",
            "total"
        ]

        read_only_fields = [
            "id",
            "cliente",
            "descricao",
            "data_pedido",
            "itens",
            "total"
        ]

    def get_total(self, obj):
        return obj.total()
