from flask import Flask, request, jsonify, send_from_directory, render_template_string
from flask_cors import CORS
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import time
import random
import json
import os
import base64
from datetime import datetime
from io import BytesIO
from PIL import Image
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

app = Flask(__name__)
CORS(app)

# HTML do index embutido no Python
HTML_TEMPLATE = '''<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Instituto ELO - Consulta CNPJ</title>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 20px;
        }

        .container {
            max-width: 1200px;
            width: 100%;
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            overflow: hidden;
        }

        .header {
            background: linear-gradient(135deg, #1a237e 0%, #0d47a1 100%);
            padding: 30px;
            text-align: center;
            color: white;
            position: relative;
        }

        .logo-container {
            margin-bottom: 15px;
        }

        .logo {
            width: 120px;
            height: 120px;
            border-radius: 50%;
            border: 4px solid white;
            box-shadow: 0 5px 15px rgba(0,0,0,0.3);
            object-fit: cover;
            background: white;
        }

        .header h1 {
            font-size: 2.5em;
            margin-bottom: 5px;
            font-weight: 700;
        }

        .header p {
            font-size: 1.1em;
            opacity: 0.9;
        }

        .search-section {
            padding: 40px;
            text-align: center;
            background: #f8f9fa;
        }

        .search-box {
            display: flex;
            max-width: 600px;
            margin: 0 auto;
            gap: 10px;
            flex-wrap: wrap;
            justify-content: center;
        }

        .search-box input {
            flex: 1;
            min-width: 250px;
            padding: 15px 20px;
            border: 2px solid #e0e0e0;
            border-radius: 50px;
            font-size: 16px;
            transition: all 0.3s;
            outline: none;
        }

        .search-box input:focus {
            border-color: #1a237e;
            box-shadow: 0 0 0 3px rgba(26, 35, 126, 0.1);
        }

        .search-box button {
            padding: 15px 30px;
            background: linear-gradient(135deg, #1a237e 0%, #0d47a1 100%);
            color: white;
            border: none;
            border-radius: 50px;
            font-size: 16px;
            cursor: pointer;
            transition: all 0.3s;
            display: flex;
            align-items: center;
            gap: 10px;
            font-weight: 600;
        }

        .search-box button:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 20px rgba(0,0,0,0.2);
        }

        .search-box button:active {
            transform: translateY(0);
        }

        .search-box button:disabled {
            opacity: 0.6;
            cursor: not-allowed;
            transform: none;
        }

        .loading {
            display: none;
            text-align: center;
            padding: 20px;
        }

        .loading.active {
            display: block;
        }

        .spinner {
            width: 50px;
            height: 50px;
            border: 5px solid #f3f3f3;
            border-top: 5px solid #1a237e;
            border-radius: 50%;
            animation: spin 1s linear infinite;
            margin: 0 auto 20px;
        }

        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }

        .results {
            display: none;
            padding: 40px;
            background: white;
        }

        .results.active {
            display: block;
        }

        .result-card {
            background: white;
            border-radius: 15px;
            box-shadow: 0 5px 20px rgba(0,0,0,0.1);
            overflow: hidden;
            margin-bottom: 30px;
        }

        .result-header {
            background: linear-gradient(135deg, #1a237e 0%, #0d47a1 100%);
            color: white;
            padding: 20px;
            text-align: center;
        }

        .result-header h2 {
            font-size: 1.5em;
            margin-bottom: 5px;
        }

        .result-header .subtitle {
            opacity: 0.9;
            font-size: 0.9em;
        }

        .data-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            padding: 30px;
        }

        .data-item {
            background: #f8f9fa;
            padding: 15px;
            border-radius: 10px;
            border-left: 4px solid #1a237e;
        }

        .data-item.full-width {
            grid-column: 1 / -1;
        }

        .data-item label {
            font-size: 0.85em;
            color: #666;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            display: block;
            margin-bottom: 5px;
        }

        .data-item .value {
            font-size: 1.1em;
            color: #333;
            font-weight: 500;
            word-break: break-word;
        }

        .data-item .value.status-ativa {
            color: #2e7d32;
            font-weight: 700;
        }

        .data-item .value.status-inativa {
            color: #c62828;
            font-weight: 700;
        }

        .screenshot-section {
            padding: 20px;
            text-align: center;
            background: #f8f9fa;
            border-top: 2px solid #e0e0e0;
        }

        .screenshot-section h3 {
            margin-bottom: 15px;
            color: #1a237e;
        }

        .screenshot-section img {
            max-width: 100%;
            border-radius: 10px;
            box-shadow: 0 5px 20px rgba(0,0,0,0.1);
            border: 2px solid #e0e0e0;
        }

        .error-message {
            display: none;
            background: #ffebee;
            color: #c62828;
            padding: 15px 20px;
            border-radius: 10px;
            margin: 20px;
            text-align: center;
            border-left: 4px solid #c62828;
        }

        .error-message.active {
            display: block;
        }

        .footer {
            text-align: center;
            padding: 20px;
            background: #f8f9fa;
            color: #666;
            font-size: 0.9em;
            border-top: 1px solid #e0e0e0;
        }

        @media (max-width: 768px) {
            .header h1 {
                font-size: 1.8em;
            }
            
            .search-section {
                padding: 20px;
            }
            
            .results {
                padding: 20px;
            }
            
            .data-grid {
                grid-template-columns: 1fr;
                padding: 15px;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <!-- Cabeçalho -->
        <div class="header">
            <div class="logo-container">
                <img src="https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcTT3OT5Ab9eGIbUjkUFo2BHQIsvRP7yonUfMAJ36oqcvg&s=10" 
                     alt="Instituto ELO" 
                     class="logo">
            </div>
            <h1>Instituto ELO</h1>
            <p>Consulta de Situação Cadastral - CNPJ</p>
        </div>

        <!-- Área de Pesquisa -->
        <div class="search-section">
            <div class="search-box">
                <input type="text" 
                       id="cnpjInput" 
                       placeholder="Digite o CNPJ (00.000.000/0000-00)"
                       maxlength="18"
                       oninput="formatarCNPJ(this)">
                <button onclick="consultarCNPJ()" id="btnConsultar">
                    <i class="fas fa-search"></i>
                    Consultar
                </button>
            </div>
        </div>

        <!-- Loading -->
        <div class="loading" id="loading">
            <div class="spinner"></div>
            <p style="color: #666;">Consultando CNPJ...</p>
            <p style="color: #999; font-size: 0.9em;">Isso pode levar alguns segundos</p>
        </div>

        <!-- Mensagem de Erro -->
        <div class="error-message" id="errorMessage"></div>

        <!-- Resultados -->
        <div class="results" id="results">
            <div class="result-card">
                <div class="result-header">
                    <h2>🇧🇷 REPÚBLICA FEDERATIVA DO BRASIL</h2>
                    <div class="subtitle">CADASTRO NACIONAL DA PESSOA JURÍDICA</div>
                </div>
                
                <div class="data-grid" id="dataGrid">
                    <!-- Os dados serão inseridos aqui dinamicamente -->
                </div>

                <!-- Screenshot do Comprovante -->
                <div class="screenshot-section" id="screenshotSection" style="display: none;">
                    <h3><i class="fas fa-camera"></i> Comprovante Oficial</h3>
                    <img id="screenshotImg" src="" alt="Comprovante de Situação Cadastral">
                </div>
            </div>
        </div>

        <!-- Rodapé -->
        <div class="footer">
            <p>© 2024 Instituto ELO - Todos os direitos reservados</p>
            <p>Dados obtidos diretamente da Receita Federal do Brasil</p>
        </div>
    </div>

    <script>
        function formatarCNPJ(input) {
            let valor = input.value.replace(/\\D/g, '');
            
            if (valor.length > 14) {
                valor = valor.substring(0, 14);
            }
            
            // Aplica a máscara
            if (valor.length > 2) {
                valor = valor.substring(0, 2) + '.' + valor.substring(2);
            }
            if (valor.length > 6) {
                valor = valor.substring(0, 6) + '.' + valor.substring(6);
            }
            if (valor.length > 10) {
                valor = valor.substring(0, 10) + '/' + valor.substring(10);
            }
            if (valor.length > 15) {
                valor = valor.substring(0, 15) + '-' + valor.substring(15);
            }
            
            input.value = valor;
        }

        async function consultarCNPJ() {
            const cnpjInput = document.getElementById('cnpjInput');
            const btnConsultar = document.getElementById('btnConsultar');
            const loading = document.getElementById('loading');
            const results = document.getElementById('results');
            const errorMessage = document.getElementById('errorMessage');
            
            // Limpa mensagens anteriores
            errorMessage.classList.remove('active');
            results.classList.remove('active');
            
            const cnpj = cnpjInput.value.replace(/\\D/g, '');
            
            if (cnpj.length !== 14) {
                mostrarErro('CNPJ inválido! Digite um CNPJ com 14 dígitos.');
                return;
            }
            
            // Ativa loading
            loading.classList.add('active');
            btnConsultar.disabled = true;
            
            try {
                const response = await fetch('/consultar', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ cnpj: cnpj })
                });
                
                const data = await response.json();
                
                if (data.sucesso) {
                    exibirResultados(data.dados, data.screenshot);
                } else {
                    mostrarErro(data.erro || 'Erro ao consultar CNPJ');
                }
                
            } catch (error) {
                mostrarErro('Erro de conexão com o servidor. Verifique se o servidor está rodando.');
                console.error('Erro:', error);
            } finally {
                loading.classList.remove('active');
                btnConsultar.disabled = false;
            }
        }

        function exibirResultados(dados, screenshot) {
            const results = document.getElementById('results');
            const dataGrid = document.getElementById('dataGrid');
            const screenshotSection = document.getElementById('screenshotSection');
            const screenshotImg = document.getElementById('screenshotImg');
            
            // Mapeamento de campos para exibição
            const camposExibicao = [
                { chave: 'numero_inscricao', label: 'Número de Inscrição' },
                { chave: 'data_abertura', label: 'Data de Abertura' },
                { chave: 'nome_empresarial', label: 'Nome Empresarial' },
                { chave: 'nome_fantasia', label: 'Nome Fantasia' },
                { chave: 'situacao_cadastral', label: 'Situação Cadastral', classe: 'status' },
                { chave: 'data_situacao_cadastral', label: 'Data da Situação Cadastral' },
                { chave: 'motivo_situacao_cadastral', label: 'Motivo da Situação Cadastral' },
                { chave: 'porte', label: 'Porte' },
                { chave: 'atividade_principal', label: 'Atividade Principal' },
                { chave: 'atividades_secundarias', label: 'Atividades Secundárias' },
                { chave: 'natureza_juridica', label: 'Natureza Jurídica' },
                { chave: 'logradouro', label: 'Logradouro' },
                { chave: 'numero', label: 'Número' },
                { chave: 'complemento', label: 'Complemento' },
                { chave: 'cep', label: 'CEP' },
                { chave: 'bairro', label: 'Bairro/Distrito' },
                { chave: 'municipio', label: 'Município' },
                { chave: 'uf', label: 'UF' },
                { chave: 'email', label: 'E-mail' },
                { chave: 'telefone', label: 'Telefone' },
                { chave: 'ente_federativo', label: 'Ente Federativo (EFR)' },
                { chave: 'situacao_especial', label: 'Situação Especial' },
                { chave: 'data_situacao_especial', label: 'Data Situação Especial' },
            ];
            
            let html = '';
            
            camposExibicao.forEach(campo => {
                const valor = dados[campo.chave];
                
                if (valor && valor.trim() !== '') {
                    let classeAdicional = '';
                    let valorFormatado = valor;
                    
                    if (campo.classe === 'status') {
                        if (valor.toUpperCase() === 'ATIVA' || valor.toUpperCase() === 'ATIVO') {
                            classeAdicional = 'status-ativa';
                        } else if (valor.toUpperCase() === 'INATIVA' || valor.toUpperCase() === 'INATIVO' || 
                                   valor.toUpperCase() === 'SUSPENSA' || valor.toUpperCase() === 'BAIXADA') {
                            classeAdicional = 'status-inativa';
                        }
                    }
                    
                    // Formata atividades secundárias (quebra de linha)
                    if (campo.chave === 'atividades_secundarias') {
                        valorFormatado = valor.replace(/\\n/g, '<br>');
                    }
                    
                    html += `
                        <div class="data-item ${campo.chave === 'atividades_secundarias' || campo.chave === 'nome_empresarial' ? 'full-width' : ''}">
                            <label>${campo.label}</label>
                            <div class="value ${classeAdicional}">${valorFormatado || 'Não informado'}</div>
                        </div>
                    `;
                }
            });
            
            dataGrid.innerHTML = html;
            results.classList.add('active');
            
            // Exibe screenshot se disponível
            if (screenshot) {
                screenshotImg.src = screenshot;
                screenshotSection.style.display = 'block';
            } else {
                screenshotSection.style.display = 'none';
            }
            
            // Scroll até os resultados
            results.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }

        function mostrarErro(mensagem) {
            const errorMessage = document.getElementById('errorMessage');
            errorMessage.innerHTML = `<i class="fas fa-exclamation-triangle"></i> ${mensagem}`;
            errorMessage.classList.add('active');
            
            // Scroll até a mensagem
            errorMessage.scrollIntoView({ behavior: 'smooth', block: 'center' });
            
            // Esconde após 5 segundos
            setTimeout(() => {
                errorMessage.classList.remove('active');
            }, 5000);
        }

        // Permite consultar pressionando Enter
        document.getElementById('cnpjInput').addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                consultarCNPJ();
            }
        });
    </script>
</body>
</html>'''

class ConsultaCNPJHeadless:
    """Classe para consulta de CNPJ em modo headless"""
    
    def __init__(self):
        self.driver = None
        
    def iniciar_driver_headless(self):
        """Inicia o Chrome em modo headless (sem interface gráfica)"""
        chrome_options = Options()
        
        # Modo headless (não abre janela)
        chrome_options.add_argument('--headless=new')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1366,768')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        chrome_options.add_argument('--ignore-certificate-errors')
        chrome_options.add_argument('--ignore-ssl-errors')
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36')
        
        self.driver = webdriver.Chrome(options=chrome_options)
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
    def capturar_screenshot(self):
        """Captura screenshot da página e converte para base64"""
        try:
            # Captura o screenshot
            screenshot = self.driver.get_screenshot_as_png()
            
            # Converte para base64
            screenshot_base64 = base64.b64encode(screenshot).decode('utf-8')
            
            return f"data:image/png;base64,{screenshot_base64}"
        except Exception as e:
            print(f"Erro ao capturar screenshot: {str(e)}")
            return None
    
    def clicar_captcha(self):
        """Clica no captcha de forma robusta"""
        try:
            # Procura iframe do hCaptcha
            iframes = self.driver.find_elements(By.TAG_NAME, "iframe")
            
            for iframe in iframes:
                try:
                    src = iframe.get_attribute('src') or ''
                    
                    if 'hcaptcha' in src.lower() or 'captcha' in src.lower():
                        # Scroll até o iframe
                        self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", iframe)
                        time.sleep(0.5)
                        
                        # Tenta clicar dentro do iframe
                        self.driver.switch_to.frame(iframe)
                        
                        try:
                            checkbox = WebDriverWait(self.driver, 3).until(
                                EC.element_to_be_clickable((By.CSS_SELECTOR, "#checkbox"))
                            )
                            checkbox.click()
                            self.driver.switch_to.default_content()
                            return True
                        except:
                            self.driver.switch_to.default_content()
                            
                except:
                    continue
            
            # Método alternativo: clicar por JavaScript
            script = """
            var checkbox = document.querySelector('#checkbox[role="checkbox"]');
            if (checkbox) {
                checkbox.click();
                return true;
            }
            return false;
            """
            return self.driver.execute_script(script)
            
        except Exception as e:
            print(f"Erro ao clicar captcha: {str(e)}")
            return False
    
    def consultar_cnpj(self, cnpj):
        """Realiza a consulta completa do CNPJ"""
        resultado_dados = {}
        screenshot = None
        
        try:
            # Inicia o driver
            self.iniciar_driver_headless()
            
            # Acessa o site
            self.driver.get("https://solucoes.receita.fazenda.gov.br/Servicos/cnpjreva/")
            time.sleep(3)
            
            # Encontra o campo do CNPJ
            campo_cnpj = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='text']"))
            )
            
            # Digita o CNPJ
            campo_cnpj.click()
            time.sleep(0.5)
            
            for char in cnpj:
                campo_cnpj.send_keys(char)
                time.sleep(random.uniform(0.03, 0.1))
            
            time.sleep(1)
            
            # Clica no captcha
            self.clicar_captcha()
            time.sleep(3)
            
            # Clica no botão Consultar
            try:
                botao_consultar = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Consultar')]"))
                )
                
                actions = ActionChains(self.driver)
                actions.move_to_element(botao_consultar)
                actions.pause(random.uniform(0.3, 0.7))
                actions.click()
                actions.perform()
                
            except Exception as e:
                print(f"Erro ao clicar Consultar: {str(e)}")
                try:
                    self.driver.execute_script("arguments[0].click();", botao_consultar)
                except:
                    pass
            
            # Aguarda o resultado
            time.sleep(5)
            
            # Extrai os dados
            resultado_dados = self.extrair_dados(cnpj)
            
            # Só tira print se conseguiu puxar os dados
            if resultado_dados and len(resultado_dados) > 2:
                screenshot = self.capturar_screenshot()
            
            return {
                'sucesso': True,
                'dados': resultado_dados,
                'screenshot': screenshot
            }
            
        except Exception as e:
            print(f"Erro na consulta: {str(e)}")
            return {
                'sucesso': False,
                'erro': str(e),
                'dados': resultado_dados,
                'screenshot': None
            }
        finally:
            if self.driver:
                self.driver.quit()
    
    def extrair_dados(self, cnpj):
        """Extrai todos os dados da página de resultado"""
        dados = {
            'cnpj_consultado': cnpj,
            'data_consulta': datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        }
        
        try:
            # Aguarda o resultado
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CLASS_NAME, "content-box"))
            )
            
            # Mapeamento completo de campos
            campos = {
                "NÚMERO DE INSCRIÇÃO": "numero_inscricao",
                "DATA DE ABERTURA": "data_abertura",
                "NOME EMPRESARIAL": "nome_empresarial",
                "TÍTULO DO ESTABELECIMENTO (NOME DE FANTASIA)": "nome_fantasia",
                "SITUAÇÃO CADASTRAL": "situacao_cadastral",
                "DATA DA SITUAÇÃO CADASTRAL": "data_situacao_cadastral",
                "MOTIVO DE SITUAÇÃO CADASTRAL": "motivo_situacao_cadastral",
                "SITUAÇÃO ESPECIAL": "situacao_especial",
                "DATA DA SITUAÇÃO ESPECIAL": "data_situacao_especial",
                "LOGRADOURO": "logradouro",
                "NÚMERO": "numero",
                "COMPLEMENTO": "complemento",
                "CEP": "cep",
                "BAIRRO/DISTRITO": "bairro",
                "MUNICÍPIO": "municipio",
                "UF": "uf",
                "ENDEREÇO ELETRÔNICO": "email",
                "TELEFONE": "telefone",
                "PORTE": "porte",
                "CÓDIGO E DESCRIÇÃO DA ATIVIDADE ECONÔMICA PRINCIPAL": "atividade_principal",
                "CÓDIGO E DESCRIÇÃO DAS ATIVIDADES ECONÔMICAS SECUNDÁRIAS": "atividades_secundarias",
                "CÓDIGO E DESCRIÇÃO DA NATUREZA JURÍDICA": "natureza_juridica",
                "ENTE FEDERATIVO RESPONSÁVEL (EFR)": "ente_federativo",
            }
            
            for titulo, chave in campos.items():
                try:
                    elementos = self.driver.find_elements(By.XPATH, 
                        f"//div[contains(text(), '{titulo}')]/following-sibling::div[@class='section-data']")
                    
                    if elementos:
                        valor = elementos[0].text.strip()
                        if valor and valor != "********":
                            dados[chave] = valor
                except:
                    pass
            
            # Extrai atividades secundárias (podem ser múltiplas)
            try:
                atividades_sec = self.driver.find_elements(By.XPATH,
                    "//div[contains(text(), 'ATIVIDADES ECONÔMICAS SECUNDÁRIAS')]/following-sibling::div[@class='section-data']")
                
                if atividades_sec:
                    # Pega todo o texto incluindo <br>
                    texto_completo = atividades_sec[0].get_attribute('innerHTML')
                    texto_completo = texto_completo.replace('<br _ngcontent-ng-c1048813218="" class="ng-star-inserted">', '\n')
                    texto_completo = texto_completo.replace('<!---->', '')
                    dados['atividades_secundarias'] = texto_completo.strip()
            except:
                pass
            
            return dados
            
        except Exception as e:
            print(f"Erro ao extrair dados: {str(e)}")
            return dados


@app.route('/')
def index():
    """Serve a página HTML"""
    return render_template_string(HTML_TEMPLATE)


@app.route('/consultar', methods=['POST'])
def consultar():
    """Endpoint para consulta de CNPJ"""
    try:
        data = request.json
        cnpj = data.get('cnpj', '').strip()
        
        # Limpa o CNPJ
        cnpj = ''.join(filter(str.isdigit, cnpj))
        
        if len(cnpj) != 14:
            return jsonify({
                'sucesso': False,
                'erro': 'CNPJ inválido! Deve conter 14 dígitos.'
            })
        
        print(f"Consultando CNPJ: {cnpj}")
        
        # Realiza a consulta
        consultor = ConsultaCNPJHeadless()
        resultado = consultor.consultar_cnpj(cnpj)
        
        return jsonify(resultado)
        
    except Exception as e:
        return jsonify({
            'sucesso': False,
            'erro': f'Erro interno: {str(e)}'
        })


if __name__ == '__main__':
    print("="*60)
    print("🏢 INSTITUTO ELO - CONSULTA CNPJ")
    print("="*60)
    print(f"🚀 Servidor iniciado em: http://localhost:5000")
    print(f"📡 Modo: Headless (sem abrir navegador)")
    print("="*60)
    
    app.run(host='0.0.0.0', port=5000, debug=True)
