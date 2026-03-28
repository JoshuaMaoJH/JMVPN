import keyring
import keyring.errors

_SERVICE = "jmvpn"

def _key(server_id: str) -> str:
    return f"jmvpn-{server_id}"

def get_credential(server_id: str) -> str | None:
    return keyring.get_password(_SERVICE, _key(server_id))

def set_credential(server_id: str, secret: str) -> None:
    keyring.set_password(_SERVICE, _key(server_id), secret)

def delete_credential(server_id: str) -> None:
    try:
        keyring.delete_password(_SERVICE, _key(server_id))
    except keyring.errors.PasswordDeleteError:
        pass
