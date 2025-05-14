import os
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient

# 替换为你的Key Vault名称
KEY_VAULT_NAME = os.getenv('AZURE_KEY_VAULT_NAME', 'test-key-vault-101')
SECRET_NAME = 'hr-service-open-ai'

KVUri = f"https://{KEY_VAULT_NAME}.vault.azure.net"

# 获取凭据并创建客户端
credential = DefaultAzureCredential()
client = SecretClient(vault_url=KVUri, credential=credential)

# 读取机密
try:
    secret = client.get_secret(SECRET_NAME)
    print(f"机密 '{SECRET_NAME}' 的值: {secret.value}")
except Exception as e:
    print(f"读取机密失败: {e}") 