from modules.accounting.infrastructure.django_models import SriCredentialModel
from modules.accounting.infrastructure.sri_scraper import SriExtractorService
from cryptography.fernet import Fernet
import os
from selenium.webdriver.common.by import By
from decimal import Decimal

def encrypt_password(password: str) -> str:
    key = os.environ.get('ENCRYPTION_KEY', 'dm2FCCyLaf3HYkkJ_HbjbZEpF2EPFwBl4HH1kDec8Rg=') # Demo key
    f = Fernet(key)
    return f.encrypt(password.encode()).decode()

def decrypt_password(encrypted: str) -> str:
    key = os.environ.get('ENCRYPTION_KEY', 'dm2FCCyLaf3HYkkJ_HbjbZEpF2EPFwBl4HH1kDec8Rg=')
    f = Fernet(key)
    return f.decrypt(encrypted.encode()).decode()

class SetupSriCredentialsUseCase:
    def execute(self, tenant_id: int, ruc: str, password: str = ""):
        enc_pass = encrypt_password(password) if password else ""
        cred, created = SriCredentialModel.objects.update_or_create(
            tenant_id=tenant_id,
            defaults={'ruc': ruc, 'encrypted_password': enc_pass}
        )
        return cred

class RunSriExtractionUseCase:
    def execute(self, tenant_id: int, month: int, year: int) -> dict:
        try:
            cred = SriCredentialModel.objects.get(tenant_id=tenant_id)
        except SriCredentialModel.DoesNotExist:
            raise Exception("RUC no configurado para esta empresa.")
        
        password = ""
        if cred.encrypted_password:
            try:
                password = decrypt_password(cred.encrypted_password)
            except:
                pass
        
        scraper = SriExtractorService(tenant_id=tenant_id, ruc=cred.ruc, password=password)
        
        # 1. Ejecutar extracción de Perfil Público (SIN LOGIN)
        scraper.sync_ruc_profile()
        
        # 2. Desactivado temporalmente a petición del usuario: "para las facturas tengo un plan"
        inserted = 0
                
        return {'status': 'success', 'inserted': inserted}

class RunSriInvoiceExtractionUseCase:
    def execute(self, tenant_id: int, month: int, year: int) -> int:
        from modules.accounting.infrastructure.django_models import SriCredentialModel, SriInboxModel
        
        cred = SriCredentialModel.objects.filter(tenant_id=tenant_id).first()
        if not cred:
            raise Exception("No hay credenciales configuradas para esta empresa.")
        
        if not cred.encrypted_password:
            raise Exception("Credenciales SRI no configuradas para esta empresa. Falta contraseña.")
            
        try:
            password = decrypt_password(cred.encrypted_password)
        except:
            raise Exception("Credenciales SRI inválidas (error de desencriptación).")
            
        scraper = SriExtractorService(tenant_id=tenant_id, ruc=cred.ruc, password=password)
        
        inserted = 0
        if scraper.login():
            try:
                import time
                from selenium.webdriver.support.ui import WebDriverWait, Select
                from selenium.webdriver.support import expected_conditions as EC
                from selenium.webdriver.common.by import By
                from bs4 import BeautifulSoup
                
                # 0. Abrir el menú lateral (Hamburguesa)
                scraper.driver.execute_script("if(typeof mostrarOcultaSidebar === 'function') mostrarOcultaSidebar();")
                time.sleep(1)
                
                # 1. Expandir menu "Facturacion Electronica" (usando JS para evitar problemas de visibilidad)
                script_fact = """
                var elements = document.getElementsByTagName('a');
                var fact = null;
                for(var i=0; i<elements.length; i++) {
                    if(elements[i].textContent.toLowerCase().includes('facturaci') && elements[i].textContent.toLowerCase().includes('nica')) {
                        fact = elements[i];
                        break;
                    }
                }
                if(fact) fact.click();
                """
                scraper.driver.execute_script(script_fact)
                time.sleep(2)
                
                # 2. Clic en "Comprobantes electronicos recibidos"
                script_comp = """
                var elements = document.getElementsByTagName('a');
                var comp = null;
                for(var i=0; i<elements.length; i++) {
                    if(elements[i].textContent.toLowerCase().includes('comprobantes') && elements[i].textContent.toLowerCase().includes('recibidos')) {
                        comp = elements[i];
                        break;
                    }
                }
                if(comp) comp.click();
                """
                scraper.driver.execute_script(script_comp)
                
                # 3. Esperar que cargue el formulario
                WebDriverWait(scraper.driver, 15).until(
                    EC.presence_of_element_located((By.ID, "frmPrincipal:ano"))
                )
                time.sleep(2)
                
                import datetime
                now = datetime.datetime.now()
                
                if month == 0:
                    if int(year) == now.year:
                        months_to_sync = range(1, now.month + 1)
                    else:
                        months_to_sync = range(1, 13)
                else:
                    months_to_sync = [month]
                    
                total_inserted = 0
                
                for m in months_to_sync:
                    # 4. Llenar el formulario
                    # Año
                    Select(scraper.driver.find_element(By.ID, "frmPrincipal:ano")).select_by_visible_text(str(year))
                    time.sleep(0.5)
                    # Mes
                    Select(scraper.driver.find_element(By.ID, "frmPrincipal:mes")).select_by_value(str(m))
                    time.sleep(0.5)
                    # Día: "Todos" (valor 0)
                    Select(scraper.driver.find_element(By.ID, "frmPrincipal:dia")).select_by_value("0")
                    time.sleep(0.5)
                    # Tipo: Factura
                    Select(scraper.driver.find_element(By.ID, "frmPrincipal:cmbTipoComprobante")).select_by_visible_text("Factura")
                    time.sleep(0.5)
                    
                    # Mark the current table as stale before clicking
                    try:
                        scraper.driver.execute_script("var t = document.getElementById('frmPrincipal:tablaCompRecibidos'); if(t) t.setAttribute('data-stale', 'true');")
                    except:
                        pass
                        
                    # 5. Consultar
                    btn_consultar = scraper.driver.find_element(By.ID, "frmPrincipal:btnConsultarSinRe")
                    scraper.driver.execute_script("arguments[0].click();", btn_consultar)
                    
                    # 6. Esperar a que cargue la tabla de resultados
                    try:
                        # Wait for the table to lose the 'data-stale' attribute (meaning JSF replaced it)
                        WebDriverWait(scraper.driver, 10).until(
                            lambda d: not d.find_elements(By.XPATH, "//*[@id='frmPrincipal:tablaCompRecibidos' and @data-stale='true']")
                        )
                        time.sleep(1) # Give it a second to render
                        
                        WebDriverWait(scraper.driver, 5).until(
                            EC.presence_of_element_located((By.ID, "frmPrincipal:tablaCompRecibidos"))
                        )
                        
                        # 7. Extraer la tabla del HTML
                        soup = BeautifulSoup(scraper.driver.page_source, 'html.parser')
                        tabla = soup.find(id="frmPrincipal:tablaCompRecibidos")
                        
                        if tabla:
                            filas = tabla.find('tbody').find_all('tr')
                            for index, fila in enumerate(filas):
                                cols = fila.find_all('td')
                                if len(cols) >= 9:
                                    # Parsear columnas
                                    ruc_razon = cols[1].get_text(separator='|', strip=True).split('|')
                                    supplier_ruc = ruc_razon[0] if len(ruc_razon) > 0 else "DESCONOCIDO"
                                    supplier_name = ruc_razon[1] if len(ruc_razon) > 1 else "DESCONOCIDO"
                                    
                                    tipo_serie = cols[2].get_text(strip=True)
                                    doc_number = tipo_serie.replace("Factura", "").strip()
                                    
                                    access_key = cols[3].get_text(strip=True)
                                    
                                    fecha_str = cols[5].get_text(strip=True)
                                    import datetime
                                    try:
                                        em_date = datetime.datetime.strptime(fecha_str, "%d/%m/%Y").date()
                                    except:
                                        em_date = datetime.date(year, m, 1)
                                        
                                    importe_str = cols[8].get_text(strip=True).replace(',', '.')
                                    try:
                                        total_amount = Decimal(importe_str)
                                    except:
                                        total_amount = Decimal('0.00')
                                        
                                    from modules.accounting.infrastructure.django_models import SriInboxModel
                                    
                                    bad_docs = SriInboxModel.objects.filter(access_key=access_key)
                                    for b in bad_docs:
                                        if 'Fallo' in b.xml_content or 'Error' in b.xml_content:
                                            b.delete()
                                            
                                    exists = SriInboxModel.objects.filter(access_key=access_key).exists()
                                    if not exists:
                                        import requests
                                        import xml.etree.ElementTree as ET
                                        import glob
                                        import os
                                        import time
                                        
                                        xml_content = "<xml>Generado por Bot SRI (Fallo descarga SOAP)</xml>"
                                        soap_success = False
                                        err_msg = ""
                                        
                                        soap_url_offline = 'https://cel.sri.gob.ec/comprobantes-electronicos-ws/AutorizacionComprobantesOffline'
                                        soap_url_online = 'https://cel.sri.gob.ec/comprobantes-electronicos-ws/AutorizacionComprobantes'
                                        soap_headers = {'content-type': 'text/xml;charset=UTF-8'}
                                        soap_body = f'''<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:ec="http://ec.gob.sri.ws.autorizacion">
                                           <soapenv:Header/>
                                           <soapenv:Body>
                                              <ec:autorizacionComprobante>
                                                 <claveAccesoComprobante>{access_key}</claveAccesoComprobante>
                                              </ec:autorizacionComprobante>
                                           </soapenv:Body>
                                        </soapenv:Envelope>'''
                                        
                                        def try_soap(url):
                                            try:
                                                resp = requests.post(url, data=soap_body.encode('utf-8'), headers=soap_headers, timeout=10, verify=False)
                                                if resp.status_code == 200:
                                                    if "numeroComprobantes>0</" in resp.text:
                                                        return None, "0 comprobantes"
                                                    root = ET.fromstring(resp.text)
                                                    comp_node = root.find('.//comprobante')
                                                    if comp_node is not None and comp_node.text:
                                                        return comp_node.text, None
                                                return None, f"HTTP {resp.status_code}"
                                            except Exception as ex:
                                                return None, f"ConnErr: {str(ex)}"
                                                
                                        content, err1 = try_soap(soap_url_offline)
                                        if content:
                                            xml_content = content
                                            soap_success = True
                                        else:
                                            content, err2 = try_soap(soap_url_online)
                                            if content:
                                                xml_content = content
                                                soap_success = True
                                            else:
                                                err_msg = f"Offline({err1}) Online({err2})"
                                                
                                        if not soap_success:
                                            # FALLBACK A DESCARGA WEB (SELENIUM)
                                            try:
                                                # Limpiar carpeta temp
                                                for f in glob.glob(os.path.join(scraper.download_dir, "*.xml")):
                                                    os.remove(f)
                                                    
                                                # Clicar link en la web
                                                link_id = f"frmPrincipal:tablaCompRecibidos:{index}:lnkXml"
                                                scraper.driver.execute_script(f"mojarra.jsfcljs(document.getElementById('frmPrincipal'),{{'{link_id}':'{link_id}'}},'');")
                                                
                                                # Esperar hasta 10 segundos
                                                downloaded_file = None
                                                for _ in range(20):
                                                    time.sleep(0.5)
                                                    files = glob.glob(os.path.join(scraper.download_dir, "*.xml"))
                                                    if files:
                                                        downloaded_file = files[0]
                                                        break
                                                        
                                                if downloaded_file:
                                                    with open(downloaded_file, 'r', encoding='utf-8') as df:
                                                        xml_content = df.read()
                                                    os.remove(downloaded_file)
                                                else:
                                                    xml_content = f"<xml>Error: SOAP falló [{err_msg}] y descarga Web excedió el tiempo límite.</xml>"
                                            except Exception as e_sel:
                                                xml_content = f"<xml>Error: SOAP falló [{err_msg}]. Intento Web falló: {str(e_sel)}</xml>"

                                        SriInboxModel.objects.create(
                                            tenant_id=scraper.tenant_id,
                                            supplier_name=supplier_name,
                                            supplier_ruc=supplier_ruc,
                                            document_type="Factura",
                                            document_number=doc_number,
                                            access_key=access_key,
                                            xml_content=xml_content,
                                            emission_date=em_date,
                                            total_amount=total_amount,
                                            status='received'
                                        )
                                        total_inserted += 1
                    except Exception as loop_e:
                        print(f"Timeout o sin resultados para mes {m}: {loop_e}")
                        continue
                
                scraper.driver.quit()
                return total_inserted
            except Exception as e:
                import traceback
                with open('scratch/sri_error.log', 'w') as f:
                    f.write(traceback.format_exc())
                scraper.driver.quit()
                raise e
            inserted = scraper.sync_received_documents(month, year)
        else:
            raise Exception("Error de inicio de sesión en el SRI. Verifique su RUC y contraseña.")
            
        return {'status': 'success', 'inserted': inserted}

class SyncSriEmittedDocumentsUseCase:
    def execute(self, tenant_id: int, month: int, year: int, env: str = 'produccion') -> int:
        from modules.accounting.infrastructure.django_models import SriCredentialModel, SriOutboxModel
        from modules.accounting.infrastructure.sri_scraper import SriExtractorService
        import time
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait, Select
        from selenium.webdriver.support import expected_conditions as EC
        from bs4 import BeautifulSoup
        from decimal import Decimal
        import datetime
        
        try:
            cred = SriCredentialModel.objects.get(tenant_id=tenant_id)
        except SriCredentialModel.DoesNotExist:
            raise Exception("RUC no configurado para esta empresa.")
            
        ruc = cred.ruc
        password = decrypt_password(cred.encrypted_password)
        
        scraper = SriExtractorService(tenant_id, ruc, password)
        try:
            if not scraper.login():
                raise Exception("Fallo en autenticacion con el SRI")
            
            # Navegacion robusta para hacer clic directamente en el submenu
            target_index = 1 if env == 'pruebas' else 0
            
            # Navegacion robusta para expandir el arbol y hacer clic en Consultas
            script_nav = f"""
            function findExact(text) {{
                var els = document.getElementsByTagName('a');
                for(var i=0; i<els.length; i++) {{
                    if(els[i].textContent.trim() === text) return els[i];
                }}
                return null;
            }}
            function findIncludes(t1, t2) {{
                var els = document.getElementsByTagName('a');
                for(var i=0; i<els.length; i++) {{
                    var txt = els[i].textContent.toLowerCase();
                    if(txt.includes(t1) && txt.includes(t2)) return els[i];
                }}
                return null;
            }}
            
            // 1. Asegurar que Facturacion Electronica este expandido
            var pruebas = findExact('Pruebas');
            if (!pruebas) {{
                var fact = findIncludes('facturaci', 'nica');
                if (fact) fact.click();
            }}
            """
            scraper.driver.execute_script(script_nav)
            time.sleep(2)
            
            script_nav2 = f"""
            function findExact(text) {{
                var els = document.getElementsByTagName('a');
                for(var i=0; i<els.length; i++) {{
                    if(els[i].textContent.trim() === text) return els[i];
                }}
                return null;
            }}
            
            // 2. Asegurar que Pruebas o Produccion este expandido
            // Para saber si estan expandidos, contamos cuantos 'Consultas' hay.
            var els = document.getElementsByTagName('a');
            var consultas = [];
            for(var i=0; i<els.length; i++) {{
                if(els[i].textContent.trim() === 'Consultas') consultas.push(els[i]);
            }}
            
            var target_env = '{'Pruebas' if env == 'pruebas' else 'Producción'}';
            var required_consultas = (target_env === 'Pruebas') ? 2 : 1;
            
            if (consultas.length < required_consultas) {{
                var envLink = findExact(target_env);
                if (envLink) envLink.click();
            }}
            """
            scraper.driver.execute_script(script_nav2)
            time.sleep(2)
            
            script_nav3 = f"""
            // 3. Clic en Consultas
            var els = document.getElementsByTagName('a');
            var consultas = [];
            for(var i=0; i<els.length; i++) {{
                if(els[i].textContent.trim() === 'Consultas') consultas.push(els[i]);
            }}
            var target_index = {'1' if env == 'pruebas' else '0'};
            if (consultas.length > target_index) {{
                consultas[target_index].click();
            }} else if (consultas.length > 0) {{
                consultas[0].click();
            }}
            """
            scraper.driver.execute_script(script_nav3)
            
            # 2. Esperar que cargue menu.jsf
            WebDriverWait(scraper.driver, 15).until(
                EC.url_contains("menu.jsf")
            )
            time.sleep(3)
            
            # 3. Clic en "Comprobantes electronicos emitidos" dentro de menu.jsf
            script_emitidos = """
            var els = document.getElementsByTagName('a');
            for(var i=0; i<els.length; i++) {
                var txt = els[i].textContent.toLowerCase();
                if (txt.includes('comprobantes') && txt.includes('emitidos')) {
                    els[i].click();
                    break;
                }
            }
            """
            scraper.driver.execute_script(script_emitidos)
            time.sleep(5)
            
            # 3. Esperar que cargue el formulario en la ventana o iframe actual
            WebDriverWait(scraper.driver, 15).until(
                EC.url_contains("menu.jsf")
            )
            time.sleep(2)
            
            # TODO: Completar el formulario de Emitidos
            # El formulario tiene Fecha emisión, Establecimiento, Punto de emisión, etc.
            # Por ahora solo dejamos que no se cierre para ver los IDs
            # Formatear la fecha y hacer el bucle de dias
            import calendar
            from datetime import date
            
            inserted = 0
            today = date.today()
            months_to_process = [month] if month > 0 else list(range(1, 13))
            
            for m in months_to_process:
                if year == today.year and m > today.month:
                    break
                    
                _, last_day = calendar.monthrange(year, m)
                
                if year == today.year and m == today.month:
                    last_day = min(last_day, today.day)
                    
                for day in range(1, last_day + 1):
                    dia_str = f"{day:02d}/{m:02d}/{year}"
                    
                    try:
                        date_input = scraper.driver.find_element(By.ID, "frmPrincipal:calendarFechaDesde_input")
                        date_input.clear()
                        date_input.send_keys(dia_str)
                        
                        btn_consultar = scraper.driver.find_element(By.ID, "frmPrincipal:btnConsultar")
                        scraper.driver.execute_script("arguments[0].click();", btn_consultar)
                        
                        time.sleep(1.5)
                        
                        warnings = scraper.driver.find_elements(By.CSS_SELECTOR, ".ui-messages-warn-summary")
                        no_data = False
                        for w in warnings:
                            if "No existen datos" in w.text:
                                no_data = True
                                break
                                
                        if not no_data:
                            soup = BeautifulSoup(scraper.driver.page_source, 'html.parser')
                            tabla = soup.find(id="frmPrincipal:tablaCompEmitidos") or soup.find(class_="ui-datatable-data")
                            
                            if tabla:
                                filas = tabla.find_all('tr')
                                for fila in filas:
                                    cols = fila.find_all('td')
                                    if len(cols) >= 3 and "Factura" in cols[1].get_text():
                                        tipo_serie = cols[1].get_text(strip=True)
                                        parts = tipo_serie.split(' ', 1)
                                        tipo = parts[0] if len(parts) > 0 else "Factura"
                                        doc_number = parts[1] if len(parts) > 1 else ""
                                        access_key = cols[2].get_text(strip=True)
                                        
                                        fecha_str = cols[3].get_text(strip=True) if len(cols) > 3 else dia_str
                                        customer_ruc = cols[4].get_text(strip=True) if len(cols) > 4 else "9999999999999"
                                        customer_name = cols[5].get_text(strip=True) if len(cols) > 5 else "CLIENTE SA"
                                        
                                        try:
                                            em_date = datetime.datetime.strptime(fecha_str.split(' ')[0], "%d/%m/%Y").date()
                                        except:
                                            em_date = datetime.date(year, m, day)
                                            
                                        exists = SriOutboxModel.objects.filter(access_key=access_key).exists()
                                        if not exists:
                                            import requests
                                            import xml.etree.ElementTree as ET
                                            
                                            xml_content = "<xml>Generado por Bot SRI (Fallo descarga SOAP)</xml>"
                                            total_amount = Decimal('0.00')
                                            
                                            if env == 'pruebas':
                                                soap_url_offline = 'https://celcer.sri.gob.ec/comprobantes-electronicos-ws/AutorizacionComprobantesOffline'
                                                soap_url_online = 'https://celcer.sri.gob.ec/comprobantes-electronicos-ws/AutorizacionComprobantes'
                                            else:
                                                soap_url_offline = 'https://cel.sri.gob.ec/comprobantes-electronicos-ws/AutorizacionComprobantesOffline'
                                                soap_url_online = 'https://cel.sri.gob.ec/comprobantes-electronicos-ws/AutorizacionComprobantes'
                                                
                                            soap_headers = {
                                                'content-type': 'text/xml;charset=UTF-8',
                                                'User-Agent': 'Mozilla/5.0'
                                            }
                                            soap_body = f'''<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:ec="http://ec.gob.sri.ws.autorizacion">
                                               <soapenv:Header/>
                                               <soapenv:Body>
                                                  <ec:autorizacionComprobante>
                                                     <claveAccesoComprobante>{access_key}</claveAccesoComprobante>
                                                  </ec:autorizacionComprobante>
                                               </soapenv:Body>
                                            </soapenv:Envelope>'''
                                            
                                            def try_soap(url):
                                                try:
                                                    resp = requests.post(url, data=soap_body.encode('utf-8'), headers=soap_headers, timeout=10, verify=False)
                                                    if resp.status_code == 200:
                                                        root = ET.fromstring(resp.text)
                                                        comp_node = root.find('.//comprobante')
                                                        if comp_node is not None and comp_node.text:
                                                            return comp_node.text
                                                    return None
                                                except:
                                                    return None
                                                    
                                            content = try_soap(soap_url_offline)
                                            if not content:
                                                content = try_soap(soap_url_online)
                                                
                                            if content:
                                                xml_content = content
                                                import re
                                                total_match = re.search(r'<importeTotal>([\d\.]+)</importeTotal>', xml_content)
                                                ruc_match = re.search(r'<identificacionComprador>([^<]+)</identificacionComprador>', xml_content)
                                                name_match = re.search(r'<razonSocialComprador>([^<]+)</razonSocialComprador>', xml_content)
                                                
                                                if total_match:
                                                    try:
                                                        total_amount = Decimal(total_match.group(1))
                                                    except:
                                                        pass
                                                if ruc_match: customer_ruc = ruc_match.group(1)
                                                if name_match: customer_name = name_match.group(1)
                                                
                                            SriOutboxModel.objects.create(
                                                tenant_id=tenant_id,
                                                customer_name=customer_name,
                                                customer_ruc=customer_ruc,
                                                document_type=tipo,
                                                document_number=doc_number,
                                                access_key=access_key,
                                                emission_date=em_date,
                                                total_amount=total_amount,
                                                xml_content=xml_content
                                            )
                                            inserted += 1
                    except Exception as e:
                        print(f"Error en dia {dia_str}: {e}")
                        
            return inserted
            
        except Exception as e:
            raise e
        finally:
            if scraper.driver:
                scraper.driver.quit()
