import pytest
from brownie import config
from brownie import Contract
from brownie import interface, project


# @pytest.fixture
# def veHNDVoter(pm, gov, veHNDVoter):
#     Vault = pm(config["dependencies"][0]).Vault
#     vault = guardian.deploy(Vault)
#     vault.initialize(token, gov, rewards, "", "", guardian, management)
#     vault.setDepositLimit(2 ** 256 - 1, {"from": gov})
#     vault.setManagement(management, {"from": gov})
#     assert vault.token() == token.address
#     yield vault
    
    
    
#     implementation = veHNDVoter.deploy({"from": account})
    
#     # Proxy admin
#     proxy_admin = ProxyAdmin.deploy({"from": account})
    
#     # Proxy
#     box_encoded_initializer_function = encode_function_data()
#     proxy = TransparentUpgradeableProxy.deploy(
#         implementation,
#         proxy_admin,
#         box_encoded_initializer_function,
#         {"from": account, "gas_limit": 1000000},
#     )
    
@pytest.fixture
def gov(accounts):
    yield accounts[0]
    
@pytest.fixture
def oz(pm):
    yield pm(config["dependencies"][0])

# Function scoped isolation fixture to enable xdist.
# Snapshots the chain before each test and reverts after test completion.
@pytest.fixture(scope="function", autouse=True)
def shared_setup(fn_isolation):
    pass