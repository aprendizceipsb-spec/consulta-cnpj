from flask import Flask, request, jsonify, send_file, render_template_string
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
            dados = self.extrair_dados(cnpj)
            
            # Captura screenshot
            screenshot = self.capturar_screenshot()
            
            return {
                'sucesso': True,
                'dados': dados,
                'screenshot': screenshot
            }
            
        except Exception as e:
            print(f"Erro na consulta: {str(e)}")
            return {
                'sucesso': False,
                'erro': str(e)
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
    return send_file('index.html')


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
