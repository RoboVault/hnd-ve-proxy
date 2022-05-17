import pytest
from brownie import config
from brownie import Contract
from brownie import interface, project

def encode_function_data(initializer=None, *args):
    """Encodes the function call so we can work with an initializer.

    Args:
        initializer ([brownie.network.contract.ContractTx], optional):
        The initializer function we want to call. Example: `box.store`.
        Defaults to None.

        args (Any, optional):
        The arguments to pass to the initializer function

    Returns:
        [bytes]: Return the encoded bytes.
    """
    if not len(args): args = b''

    if initializer: return initializer.encode_input(*args)

    return b''

def test_proxy(oz, gov, veHNDVoter):
    implementation = veHNDVoter.deploy({"from": gov})
    
    # Proxy admin
    proxy_admin = oz.ProxyAdmin.deploy({"from": gov})
    
    # Proxy
    box_encoded_initializer_function = encode_function_data(implementation.initialize, gov.address)
    proxy = oz.TransparentUpgradeableProxy.deploy(
        implementation,
        proxy_admin,
        box_encoded_initializer_function,
        {"from": gov},
    )
    
    proxy_voter = Contract.from_abi("veHNDVoter", proxy, veHNDVoter.abi)
    
    ## check initialisation worked
    assert proxy_voter.governance() == gov
