from brownie import  accounts, config, network, project, web3, MultiStrategyProxy, veHNDVoter, Contract
from eth_utils import is_checksum_address
from pathlib import Path

import click

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


def get_address(msg: str, default: str = None) -> str:
    val = click.prompt(msg, default=default)

    # Keep asking user for click.prompt until it passes
    while True:

        if is_checksum_address(val):
            return val
        elif addr := web3.ens.address(val):
            click.echo(f"Found ENS '{val}' [{addr}]")
            return addr

        click.echo(
            f"I'm sorry, but '{val}' is not a checksummed address or valid ENS record"
        )
        # NOTE: Only display default once
        val = click.prompt(msg)

def main():
    print(f"You are using the '{network.show_active()}' network")
    dev = accounts.load(click.prompt("Account", type=click.Choice(accounts.load())))
    print(f"You are using: 'dev' [{dev.address}]")

    oz = project.load(Path.home() / ".brownie" / "packages" / config["dependencies"][0])

    implementation = veHNDVoter.deploy({"from": dev}, publish_source=True)
    proxy_admin = oz.ProxyAdmin.deploy({"from": dev}, publish_source=True)
    box_encoded_initializer_function = encode_function_data(implementation.initialize, dev.address)
    proxy = oz.TransparentUpgradeableProxy.deploy(
        implementation,
        proxy_admin,
        box_encoded_initializer_function,
        {"from": dev},
        publish_source=True
    )
    
    proxy_voter = Contract.from_abi("veHNDVoter", proxy, veHNDVoter.abi)
    multistrategy = MultiStrategyProxy.deploy({"from": dev }, publish_source=True)
    multistrategy.initialize(dev, proxy)
    proxy_voter.setStrategy(multistrategy.address, {"from": dev})

    print("DEPLOYED! Addresses:")
    print("proxy_voter ", proxy_voter.address)
    print("multistrategy ", multistrategy.address)
    print("implementation ", implementation.address)
    print("proxy_admin ", proxy_admin.address)
    
