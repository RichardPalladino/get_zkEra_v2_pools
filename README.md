# Get All UniswapV2 Pools
## Script to get all pools from UniswapV2 by querying blockchain data directly

**Description:**
This is a hack of a Python script - leveraging eth-brownie - to query all UniswapV2 compatible factories and pools to build and output a set of viable LPs and associated data.

Some LPs are void - maybe they are empty / have little reserves or give another error - and some ERC20s are also void.  I try to at least weed through the initial set of noise.  I have other (private) scripts that work with this data and do a better job of eliminating worthless LPs and ERC20s.

### (dev tasks)
1. Setup brownie and its config to handle multiple chains - I want to test this on live forks, ganache, and at least one testnet (done)
    * Maybe also alternative chains and more than just one DEX
2. Make appropriate Uniswap interfaces and import them into the script (done)
3. Start calling and printing and see what comes of it (done)

### General procedural flow:

I may describe my code here later.

` UniswapV2 factory had 149575 LPs on 2022, March 4th. `
