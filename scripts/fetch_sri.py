import sys
import requests
import json

soap_body = '''<?xml version="1.0" encoding="UTF-8"?>
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"
                  xmlns:ec="http://ec.gob.sri.ws.autorizacion">
  <soapenv:Header/>
  <soapenv:Body>
    <ec:autorizacionComprobante>
      <claveAccesoComprobante>0408202601172234505300110010010000000469017744911</claveAccesoComprobante>
    </ec:autorizacionComprobante>
  </soapenv:Body>
</soapenv:Envelope>'''
resp = requests.post('https://celcer.sri.gob.ec/comprobantes-electronicos-ws/AutorizacionComprobantesOffline', data=soap_body.encode('utf-8'), headers={'Content-Type': 'text/xml; charset=utf-8'})
with open('sri_response.xml', 'w', encoding='utf-8') as f:
    f.write(resp.text)
print("Saved to sri_response.xml")
