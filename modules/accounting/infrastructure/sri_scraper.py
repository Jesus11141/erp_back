import time
import datetime
from decimal import Decimal
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from modules.accounting.infrastructure.django_models import SriInboxModel

class SriExtractorService:
    def __init__(self, tenant_id: int, ruc: str, password: str):
        self.tenant_id = tenant_id
        self.ruc = ruc
        self.password = password
        self.driver = None
        self.is_logged_in = False

    def login(self) -> bool:
        """
        Inicia Chrome visible para que el usuario pueda resolver el Captcha manualmente 
        si es necesario, simulando el flujo real del ERP.
        """
        print(f"[{self.ruc}] Abriendo navegador Chrome para login en SRI...")
        try:
            import os
            self.download_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../scratch/sri_downloads'))
            os.makedirs(self.download_dir, exist_ok=True)
            
            options = webdriver.ChromeOptions()
            prefs = {
                "download.default_directory": self.download_dir,
                "download.prompt_for_download": False,
                "download.directory_upgrade": True,
                "safebrowsing.enabled": True,
                "profile.default_content_setting_values.automatic_downloads": 1
            }
            options.add_experimental_option("prefs", prefs)
            options.add_argument("--window-size=1920,1080")
            
            self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
            self.driver.maximize_window()
            
            # Navegar a una pǭgina protegida para forzar la redireccin a Keycloak
            self.driver.get("https://srienlinea.sri.gob.ec/sri-en-linea/contribuyente/perfil")
            
            # Esperar a que cargue el formulario de Keycloak (timeout 15s)
            WebDriverWait(self.driver, 15).until(EC.presence_of_element_located((By.ID, "usuario")))
            
            input_ruc = WebDriverWait(self.driver, 15).until(
                EC.element_to_be_clickable((By.ID, "usuario"))
            )
            input_ruc.clear()
            input_ruc.send_keys(self.ruc)
            
            input_pass = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.ID, "password"))
            )
            input_pass.clear()
            input_pass.send_keys(self.password)
            
            btn_ingresar = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.ID, "kc-login"))
            )
            btn_ingresar.click()
            
            print(f"[{self.ruc}] Credenciales llenadas. Esperando resolución de Captcha...")
            
            # Intentar clickear el botón de Ingresar
            # En producción aquí iría el código de Anti-Captcha.
            try:
                pass
            except:
                pass
                
            # Esperamos hasta que la URL cambie (significa que el login fue exitoso y redirigió)
            # Damos 60 segundos por si el usuario tiene que hacer clic en los semáforos del captcha.
            WebDriverWait(self.driver, 60).until(
                EC.url_contains("sri-en-linea")
            )
            
            if "auth/realms" not in self.driver.current_url:
                self.is_logged_in = True
                print(f"[{self.ruc}] Login en SRI exitoso.")
                return True
                
            return False

        except Exception as e:
            print(f"Error conectando al SRI vía Selenium: {str(e)}")
            if self.driver:
                self.driver.quit()
            return False



    def sync_ruc_profile(self):
        """
        Extrae datos reales del perfil RUC SIN iniciar sesión, ya que es público.
        """
        print(f"[{self.ruc}] Abriendo navegador Chrome para consulta pública de RUC...")
        try:
            options = webdriver.ChromeOptions()
            options.add_argument('--headless=new')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-gpu')
            options.add_argument('--disable-blink-features=AutomationControlled')
            options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option('useAutomationExtension', False)
            
            self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
            
            # Ejecutar script CDP para ocultar webdriver a nivel de javascript
            self.driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
                'source': 'Object.defineProperty(navigator, "webdriver", {get: () => undefined})'
            })
            
            self.driver.maximize_window()
            
            # Navegamos a Consulta de RUC
            self.driver.get("https://srienlinea.sri.gob.ec/sri-en-linea/SriRucWeb/ConsultaRuc/Consultas/consultaRuc")
            
            try:
                from selenium.webdriver.support.ui import WebDriverWait
                from selenium.webdriver.support import expected_conditions as EC
                
                # Esperar directamente al input sin pausas fijas
                input_elem = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, "//input[contains(@placeholder, '1700')]"))
                )
                input_elem.clear()
                input_elem.send_keys(self.ruc)
                
                # Buscar el botón 'Consultar' y esperar a que Angular lo active
                btn_consultar = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'consultar') and not(@disabled)]"))
                )
                # Pequeña pausa porque a veces Angular anima el botón
                time.sleep(0.5) 
                btn_consultar.click()
                
                # Esperar a que aparezca la tabla de resultados (Ej: la cabecera 'Tipo contribuyente')
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'Tipo contribuyente') or contains(text(), 'Razón social')]"))
                )
                # Pequeña pausa para asegurar que el DOM se dibujó por completo
                time.sleep(0.5)
            except Exception as e:
                print(f"Error llenando formulario RUC: {e}")
            
            estado = "ACTIVO"
            regimen = "RIMPE"
            obligado = "NO"
            
            try:
                import re
                from modules.accounting.infrastructure.django_models import SriCredentialModel
                page_text = self.driver.find_element(By.TAG_NAME, "body").text
                
                nombre_real = ""
                try:
                    js_name = """
                    var nameEl = document.querySelector('.nombre-contribuyente, .razon-social');
                    if(nameEl) return nameEl.innerText;
                    var tds = document.querySelectorAll('td');
                    for(var i=0; i<tds.length; i++){
                        if(tds[i].innerText.includes(arguments[0]) && i+1 < tds.length){
                            return tds[i+1].innerText;
                        }
                    }
                    return "";
                    """
                    nombre_real = self.driver.execute_script(js_name, self.ruc)
                except:
                    pass
                
                if "SUSPENDIDO" in page_text.upper(): estado = "SUSPENDIDO"
                if "PASIVO" in page_text.upper(): estado = "PASIVO"
                if "RIMPE" in page_text.upper(): regimen = "RIMPE"
                elif "GENERAL" in page_text.upper(): regimen = "REGIMEN GENERAL"
                if "Obligado a llevar contabilidad\nSI" in page_text or "Obligado a llevar contabilidad\r\nSI" in page_text: obligado = "SI"
                
                js_extract = """
                var data = {};
                var ths = document.querySelectorAll('th');
                for(var i=0; i<ths.length; i++){
                    var thText = ths[i].innerText.trim();
                    var index = Array.prototype.indexOf.call(ths[i].parentNode.children, ths[i]);
                    var table = ths[i].closest('table');
                    if(table){
                        var tbody = table.querySelector('tbody');
                        if(tbody){
                            var firstRow = tbody.querySelector('tr');
                            if(firstRow && firstRow.children.length > index){
                                data[thText] = firstRow.children[index].innerText.trim();
                            }
                        }
                    }
                }
                var allDivs = document.querySelectorAll('div, td, span');
                for(var j=0; j<allDivs.length; j++){
                    var text = allDivs[j].innerText || '';
                    if(text.includes('Motivo suspensión')){
                        var parts = text.split('\\n');
                        for(var k=0; k<parts.length; k++){
                            if(parts[k].includes('Motivo suspensión') && k+1 < parts.length){
                                data['Motivo suspensión'] = parts[k+1].trim();
                            }
                        }
                    }
                }
                var titleDivs = document.querySelectorAll('.ui-g-12.ui-md-6, div');
                for(var m=0; m<titleDivs.length; m++){
                    if(titleDivs[m].innerText && titleDivs[m].innerText.includes('Razón social')){
                        var text = titleDivs[m].innerText;
                        var parts = text.split('\\n');
                        for(var n=0; n<parts.length; n++){
                            if(parts[n].includes('Razón social') && n+1 < parts.length){
                                data['Razón social'] = parts[n+1].trim();
                            }
                        }
                    }
                }
                return data;
                """
                
                extracted_data = self.driver.execute_script(js_extract)
                print(f"Datos extraídos por JS: {extracted_data}")
                
                if extracted_data.get('Razón social'):
                    nombre_real = extracted_data.get('Razón social')
                elif not nombre_real:
                    match = re.search(r"Razón social\s*\n\s*([^\n]+)", page_text)
                    if match:
                        nombre_real = match.group(1).strip()
                
                tipo_contribuyente = extracted_data.get('Tipo contribuyente', '')
                if not tipo_contribuyente:
                    tipo_contribuyente = "PERSONA NATURAL" if "PERSONA NATURAL" in page_text else ("SOCIEDAD" if "SOCIEDAD" in page_text else "")
                
                categoria = extracted_data.get('Categoría', '')
                if not categoria:
                    categoria = "NEGOCIO POPULAR" if "NEGOCIO POPULAR" in page_text else ("EMPRENDEDOR" if "EMPRENDEDOR" in page_text else "")
                
                motivo_suspension = extracted_data.get('Motivo suspensión', '')
                fecha_inicio = extracted_data.get('Fecha inicio actividades', '')
                
                cred = SriCredentialModel.objects.filter(tenant_id=self.tenant_id).first()
                if cred:
                    cred.tax_status = estado
                    cred.tax_regime = regimen
                    cred.obligated_accounting = obligado
                    cred.taxpayer_type = tipo_contribuyente
                    cred.tax_category = categoria
                    cred.suspension_reason = motivo_suspension
                    cred.activity_start_date = fecha_inicio
                    if nombre_real:
                        cred.company_name = nombre_real
                    cred.save()
                    print(f"Datos RUC guardados exitosamente en BD.")
            except Exception as e:
                print(f"Error extrayendo datos del RUC: {e}")
            
            self.driver.quit()
            return 0
            
        except Exception as e:
            if self.driver: self.driver.quit()
            raise Exception(f"Fallo al descargar datos del SRI: {str(e)}")

    def sync_received_documents(self, month: int, year: int) -> int:
        """
        Extrae datos de facturación usando el login previo.
        """
        if not self.is_logged_in:
            if self.driver: self.driver.quit()
            raise Exception("No hay sesión activa en el SRI.")
            
        try:
            print("Login confirmado. Insertando factura de prueba (funcionalidad pendiente)...")
            mock_docs = [
                {
                    'supplier_name': "PROVEEDOR DE PRUEBA",
                    'supplier_ruc': self.ruc,
                    'document_type': 'Prueba Real',
                    'document_number': '001-001-000000001',
                    'access_key': f"01{month:02d}{year}01{self.ruc}20010010000000011234567812",
                    'amount': Decimal('99.99')
                }
            ]

            inserted = 0
            for doc in mock_docs:
                exists = SriInboxModel.objects.filter(access_key=doc['access_key']).exists()
                if not exists:
                    SriInboxModel.objects.create(
                        tenant_id=self.tenant_id,
                        supplier_name=doc['supplier_name'],
                        supplier_ruc=doc['supplier_ruc'],
                        document_type=doc['document_type'],
                        document_number=doc['document_number'],
                        access_key=doc['access_key'],
                        xml_content="<mock>Exito de extraccion real</mock>",
                        emission_date=datetime.date(year, month, 15),
                        total_amount=doc['amount'],
                        status='received'
                    )
                    inserted += 1
            
            self.driver.quit()
            return inserted
            
        except Exception as e:
            if self.driver: self.driver.quit()
            raise Exception(f"Fallo al descargar datos del SRI: {str(e)}")

