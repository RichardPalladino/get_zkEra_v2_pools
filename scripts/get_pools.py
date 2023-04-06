from time import perf_counter
import json

from brownie import config, network, interface
from brownie.convert import to_address

LOCAL_BLOCKCHAIN_FORKS = ["mainnet-fork", "mainnet-fork-dev"]
LOCAL_BLOCKCHAINS = LOCAL_BLOCKCHAIN_FORKS + ["development", "ganache-local", "hardhat"]

bogus_addresses = []


def serialize_sets(obj):  # so JSON can handle sets
    if isinstance(obj, set):
        return list(obj)

    return obj


def get_num_deployed() -> dict:
    factories = {}
    active_network = network.show_active()
    for dex, address in config["networks"][active_network]["factories"].items():
        try:
            factory = interface.IUniswapV2Factory(address)
        except Exception as err:
            print(
                f'Function "get_num_deployed" failed on {active_network} network {dex} factory, with the following error:\n{err}'
            )
            bogus_addresses.append(
                {
                    "factory": str(address),
                    "reason": f'interface.IUniswapV2Factory failure on {str(active_network)} with {str(dex)} factory and error "{err}"',
                }
            )
        factories[dex] = factory.allPairsLength()

    return factories


def get_pool_data(_address: str) -> dict:
    result = None
    try:
        _pool = interface.IUniswapV2Pair(_address)
        tmp_token0_address = _pool.token0()
        tmp_token1_address = _pool.token1()
        result = {
            "lp_address": _address,
            "tokens": [tmp_token0_address, tmp_token1_address],
            "reserves": _pool.getReserves(),
        }
    except Exception as err:
        print(
            f'Received the following error when querying blockchain using "get_pool_data()" for {_address}:\n  {err}'
        )
        bogus_addresses.append(
            {
                "lp_address": str(_address),
                "reason": f'error at "get_pool_data()": {err}',
            }
        )
        result = False
    finally:
        return result


def get_erc20_data(_address: str) -> dict:
    result = None
    try:
        tmp_token = interface.IERC20(_address)
        result = {
            "symbol": tmp_token.symbol(),
            "name": tmp_token.name(),
            "decimals": tmp_token.decimals(),
        }
    except Exception as err:
        print(
            f'Received the following error when querying blockchain using "get_erc20_data()" for {_address}:\n  {err}'
        )
        bogus_addresses.append(
            {
                "erc20_address": str(_address),
                "reason": f'error at "get_erc20_data()": {err}',
            }
        )
        result = False
    finally:
        return result


def main() -> None:
    start_time = perf_counter()
    factory_lps = {}
    pairs = {}
    erc_20s = {}
    factories = get_num_deployed()
    active_network = network.show_active()

    for factory_name, num_pools in factories.items():
        try:
            factory = interface.IUniswapV2Factory(
                config["networks"][active_network]["factories"][factory_name]
            )
        except Exception as err:
            print(
                f'"IUniswapV2Factory" failed on {active_network} network {factory_name} factory, with the following error:\n{err}'
            )
            bogus_addresses.append(
                {
                    "factory": str(factory_name),
                    "reason": f"interface.IUniswapV2Factory error on {str(active_network)}: {err}",
                }
            )
            continue
        factory_address = str(factory.address)
        factory_lps[factory_address] = []
        # Loop through each LP listed in the Factory
        for i in range(0, num_pools):
            try:
                tmp_lp_address = factory.allPairs(i)
            except Exception as err:
                print(
                    f"Received the following error when querying {factory} allPairs() at index {i}:\n  {err}"
                )
                bogus_addresses.append(
                    {
                        "factory": str(factory),
                        "index": str(i),
                        "reason": f'Error querying "factory.allpairs()": {err}',
                    }
                )
                # if it's bogus, make it one of my addresses for comparison
                tmp_lp_address = to_address(
                    "0x4AfA03ED8ca5972404b6bDC16Bea62b77Cf9571b"
                )
                pairs["0x4AfA03ED8ca5972404b6bDC16Bea62b77Cf9571b"] = False
            ## Get dict of pool data, if tmp_lp_address isn't bogus, i.e., has been made one of my addresses
            if tmp_lp_address != to_address(
                "0x4AfA03ED8ca5972404b6bDC16Bea62b77Cf9571b"
            ):
                pairs[tmp_lp_address] = get_pool_data(tmp_lp_address)
            if (pairs[tmp_lp_address] is None) or (pairs[tmp_lp_address] == False):
                pairs[tmp_lp_address] = False
                print(f"LP {tmp_lp_address} is invalid")
                bogus_addresses.append(
                    {
                        "lp_address": str(tmp_lp_address),
                        "reason": f"either get_pool_data() failure or one of the tokens is bad",
                    }
                )
                continue
            else:
                pairs[tmp_lp_address]["factory_address"] = factory_address
                ## Add dicts of each token data
                # Token0
                token0_address = pairs[tmp_lp_address]["tokens"][0]
                # Reduce direct blockchain calls, check if we've already populated the token data
                if token0_address in erc_20s.keys():
                    # Make sure the pool has been found and does not return an error
                    if erc_20s[token0_address] != False:
                        pairs[tmp_lp_address]["token0"] = {
                            "address": token0_address,
                            **erc_20s[token0_address],
                        }
                else:
                    # If we haven't already populated the pool data, query the blockchain to get it
                    tmp_token = get_erc20_data(token0_address)
                    # If querying the blockchain returns None for the pool, there was an error
                    if (tmp_token is None) or (tmp_token == False):
                        erc_20s[token0_address] = False
                        pairs[tmp_lp_address] = False
                        bogus_addresses.append(
                            {
                                "invalid_erc20": str(token0_address),
                                "lp_address": str(tmp_lp_address),
                                "dex_factory": str(factory_address),
                            }
                        )
                        continue
                    else:
                        erc_20s[token0_address] = tmp_token
                        pairs[tmp_lp_address]["token0"] = {
                            "address": token0_address,
                            **tmp_token,
                        }

                # Same for token1 as token0, above
                if pairs[tmp_lp_address] != False:
                    token1_address = pairs[tmp_lp_address]["tokens"][1]
                    if token1_address in erc_20s.keys():
                        if erc_20s[token1_address] != False:
                            pairs[tmp_lp_address]["token1"] = {
                                "address": token1_address,
                                **erc_20s[token1_address],
                            }
                    else:
                        tmp_token = get_erc20_data(token1_address)
                        if (tmp_token is None) or (tmp_token == False):
                            erc_20s[token1_address] = False
                            pairs[tmp_lp_address] = False
                            bogus_addresses.append(
                                {
                                    "invalid_erc20": str(token1_address),
                                    "lp_address": str(tmp_lp_address),
                                    "dex_factory": str(factory_address),
                                }
                            )
                            continue
                        else:
                            erc_20s[token1_address] = tmp_token
                            pairs[tmp_lp_address]["token1"] = {
                                "address": token1_address,
                                **tmp_token,
                            }

                # If either tokens returns an error, set the LP dictionary to False
                if (
                    (erc_20s[token0_address] == False)
                    or (erc_20s[token0_address] == False)
                    or (pairs[tmp_lp_address] == False)
                ):
                    pairs[tmp_lp_address] = False
                    print(
                        f"One of the tokens in {tmp_lp_address} is invalid, LP is invalid"
                    )
                    continue
                elif ("token0" not in pairs[tmp_lp_address]) or (
                    "token1" not in pairs[tmp_lp_address]
                ):
                    pairs[tmp_lp_address] = False
                    print(f"Missing one of the tokens in {tmp_lp_address}")
                    continue
                else:
                    # if the liquidity is excessively low, set the LP dictionary to false
                    if (
                        pairs[tmp_lp_address]["reserves"][0]
                        / (10 ** pairs[tmp_lp_address]["token0"]["decimals"])
                    ) < 1 or (
                        pairs[tmp_lp_address]["reserves"][1]
                        / (10 ** pairs[tmp_lp_address]["token1"]["decimals"])
                    ) < 1:
                        print(f"{tmp_lp_address} has too little reserves")
                        bogus_addresses.append(
                            {
                                "lp_address": str(tmp_lp_address),
                                "reason": "low reserves",
                            }
                        )
                        pairs[tmp_lp_address] = False
                    else:
                        factory_lps[factory_address].append(tmp_lp_address)
        # Close-out processing of the DEX / factory set
        print(f"{factory_name} currently has {num_pools} liquidity pools")
        # Output the current state of the pairs and LP list dictionaries
        tmp_json = json.dumps(pairs, indent=3)
        with open("lp_dictionary.json", "w") as f_out:
            f_out.write(tmp_json)
        tmp_json = json.dumps(factory_lps, indent=3)
        with open("lps_per_dex.json", "w") as f_out:
            f_out.write(tmp_json)
        tmp_json = json.dumps(bogus_addresses, indent=3)
        with open("invalid_addresses.json", "w") as f_out:
            f_out.write(tmp_json)

    end_time = perf_counter()
    total_time = (end_time - start_time) / 60
    print(f"This took {total_time} minutes.")


if __name__ == "__main__":
    main()
