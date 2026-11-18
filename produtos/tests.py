from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient
from .models import Cliente, Produto


class FluxoLojaTests(TestCase):
    def setUp(self):
        self.api = APIClient()

    def test_cadastro_login_produto_e_pedido_por_nome(self):
        resposta = self.api.post('/api/usuarios/cadastrar/', {
            'username': 'aluno_teste', 'password': 'SenhaForte123!',
            'nome': 'Aluno Teste', 'email': 'aluno_teste@example.com'
        }, format='json')
        self.assertEqual(resposta.status_code, 201, resposta.data)
        self.assertEqual(Cliente.objects.count(), 1)

        resposta = self.api.post('/api/token/', {
            'username': 'aluno_teste', 'password': 'SenhaForte123!'
        }, format='json')
        self.assertEqual(resposta.status_code, 200, resposta.data)
        self.api.credentials(HTTP_AUTHORIZATION='Bearer ' + resposta.data['access'])

        for nome, preco in [('Notebook', '3500.00'), ('Mouse', '100.00')]:
            resposta = self.api.post('/api/produtos/', {
                'nome': nome, 'quantidade': 10, 'preco': preco
            }, format='json')
            self.assertEqual(resposta.status_code, 201, resposta.data)

        resposta = self.api.post('/api/pedidos/', {
            'descricao': 'Pedido de materiais',
            'itens': [
                {'produto': 'Notebook', 'quantidade': 1},
                {'produto': 'mouse', 'quantidade': 2},
            ]
        }, format='json')
        self.assertEqual(resposta.status_code, 201, resposta.data)
        self.assertEqual(float(resposta.data['total']), 3700.0)
        self.assertEqual(resposta.data['itens'][0]['produto'], 'Notebook')
        self.assertEqual(resposta.data['itens'][1]['produto'], 'Mouse')

    def test_pedido_com_produto_inexistente_retorna_400(self):
        user = User.objects.create_user(username='u', password='Senha123456!')
        Cliente.objects.create(usuario=user, nome='Usuário', email='u@example.com')
        self.api.force_authenticate(user=user)
        resposta = self.api.post('/api/pedidos/', {'itens': [
            {'produto': 'NaoExiste', 'quantidade': 1}
        ]}, format='json')
        self.assertEqual(resposta.status_code, 400)

    def test_pedido_simples_com_nome_do_produto_quantidade_e_cliente(self):
        usuario = User.objects.create_user(username='maria', password='Senha123456!')
        Cliente.objects.create(usuario=usuario, nome='Maria Silva', email='maria@example.com')
        Produto.objects.create(nome='Teclado', quantidade=5, preco='150.00')
        self.api.force_authenticate(user=usuario)
        resposta = self.api.post('/api/pedidos/', {
            'produto': 'Teclado', 'quantidade': 2, 'cliente': 'Maria Silva'
        }, format='json')
        self.assertEqual(resposta.status_code, 201, resposta.data)
        self.assertEqual(resposta.data['cliente'], 'Maria Silva')
        self.assertEqual(resposta.data['itens'][0]['produto'], 'Teclado')
        self.assertEqual(float(resposta.data['total']), 300.0)

    def test_nao_permite_pedido_em_nome_de_outro_cliente(self):
        usuario = User.objects.create_user(username='maria', password='Senha123456!')
        Cliente.objects.create(usuario=usuario, nome='Maria Silva', email='maria@example.com')
        Produto.objects.create(nome='Teclado', quantidade=5, preco='150.00')
        self.api.force_authenticate(user=usuario)
        resposta = self.api.post('/api/pedidos/', {
            'produto': 'Teclado', 'quantidade': 2, 'cliente': 'João Silva'
        }, format='json')
        self.assertEqual(resposta.status_code, 400, resposta.data)
