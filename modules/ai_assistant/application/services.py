import os
import json
from django.conf import settings
from .tools import get_technical_service_tools, execute_tool

SYSTEM_PROMPT = """Eres Lyxa, la asistente virtual oficial con IA del taller de Servicio Técnico y ERP de la empresa.
Tu objetivo es ayudar respondiendo dudas y consultando datos reales del sistema.

REGLAS:
1. Sé amable, profesional y conciso.
2. NUNCA inventes información sobre clientes, órdenes, o estados.
3. Si te preguntan por el estado de una reparación, usa SIEMPRE tu herramienta 'buscar_estado_orden'.
4. Si la herramienta no encuentra la orden, pídele al cliente que verifique el nombre o IMEI.
5. Traduce los estados a algo más amigable (ej. RECEIVED -> Recibido, IN_REPAIR -> En Reparación, READY -> Listo, DELIVERED -> Entregado).
6. Usa Markdown para formatear tus respuestas (negritas, listas, etc.).
"""

class AIChatService:
    def __init__(self, tenant_id: int):
        self.tenant_id = tenant_id
        self.provider = os.getenv('AI_PROVIDER', 'gemini').lower()
        
    def process_chat(self, messages: list) -> str:
        # Prepend the system prompt if not present
        if not any(m.get('role') == 'system' for m in messages):
            # Gemini doesn't use 'system' role in the same way for history, but we handle it specifically below.
            pass

        if self.provider == 'openai':
            return self._process_openai(messages)
        else:
            return self._process_gemini(messages)

    def _process_openai(self, messages: list) -> str:
        from openai import OpenAI
        client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        
        # Ensure system prompt is first
        api_messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        for m in messages:
            api_messages.append({"role": m['role'], "content": m['content']})
            
        tools = get_technical_service_tools()
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=api_messages,
            tools=tools,
            tool_choice="auto"
        )
        
        response_message = response.choices[0].message
        
        # Check if function call
        if response_message.tool_calls:
            # Add assistant's tool calls to history
            api_messages.append(response_message)
            
            for tool_call in response_message.tool_calls:
                function_name = tool_call.function.name
                function_args = json.loads(tool_call.function.arguments)
                
                tool_result = execute_tool(self.tenant_id, function_name, function_args)
                
                api_messages.append({
                    "tool_call_id": tool_call.id,
                    "role": "tool",
                    "name": function_name,
                    "content": tool_result,
                })
                
            # Second call
            second_response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=api_messages
            )
            return second_response.choices[0].message.content
            
        return response_message.content

    def _process_gemini(self, messages: list) -> str:
        from google import genai
        from google.genai import types
        
        client = genai.Client(api_key=os.getenv('GEMINI_API_KEY'))
        
        # Gemini format
        contents = []
        for m in messages:
            role = "user" if m['role'] == "user" else "model"
            contents.append(types.Content(role=role, parts=[types.Part.from_text(text=m['content'])]))
            
        # Convert tools to Gemini format
        tools = get_technical_service_tools()
        gemini_tools = []
        for t in tools:
            f = t['function']
            gemini_tools.append(
                types.Tool(
                    function_declarations=[
                        types.FunctionDeclaration(
                            name=f['name'],
                            description=f['description'],
                            parameters=types.Schema(
                                type=types.Type.OBJECT,
                                properties={
                                    k: types.Schema(type=types.Type.STRING, description=v.get('description', ''))
                                    for k, v in f['parameters']['properties'].items()
                                },
                                required=f['parameters'].get('required', [])
                            )
                        )
                    ]
                )
            )

        config = types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            tools=gemini_tools,
            temperature=0.3
        )
        
        response = client.models.generate_content(
            model='gemini-3.5-flash',
            contents=contents,
            config=config
        )
        
        if response.function_calls:
            # We have a function call
            function_call = response.function_calls[0]
            name = function_call.name
            args = {k: v for k, v in function_call.args.items()}
            
            tool_result = execute_tool(self.tenant_id, name, args)
            
            # Append the model's function call
            contents.append(response.candidates[0].content)
            
            # Append the function response
            contents.append(
                types.Content(
                    role="user", 
                    parts=[
                        types.Part.from_function_response(
                            name=name,
                            response={"result": tool_result}
                        )
                    ]
                )
            )
            
            # Call again
            second_response = client.models.generate_content(
                model='gemini-3.5-flash',
                contents=contents,
                config=config
            )
            return second_response.text
            
        return response.text
