from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient

credential = DefaultAzureCredential()

secret_client = SecretClient(vault_url="https://test-key-vault-101.vault.azure.net/", credential=credential)
secret = secret_client.set_secret("secret-name", "secret-value")

print(secret.name)
print(secret.value)
print(secret.properties.version)