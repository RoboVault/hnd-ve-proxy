
// SPDX-License-Identifier: AGPL-3.0
// Feel free to change the license, but this is what we use

// Feel free to change this version of Solidity. We support >=0.6.0 <0.7.0;
pragma solidity 0.8.11;
pragma experimental ABIEncoderV2;

// These are the core Yearn libraries
import "@yearnvaults/contracts/BaseStrategy.sol";
import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/utils/math/SafeMath.sol";
import "@openzeppelin/contracts/utils/math/Math.sol";
import "@openzeppelin/contracts/utils/Address.sol";
import "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";

import {CErc20I} from "./interfaces/CErc20I.sol";
import {IUniswapV2Router02} from "./interfaces/IUniswapV2Router02.sol";

import "./MultiStrategyProxy.sol";
import "./interfaces/IERC20Extended.sol";


// USDC     0x04068DA6C83AFCFA0e13ba15A6696662335D5B75
// sUSDC    0x75EAF7dE29aEEfabe53d67515FEC4d199bF2E52F
// Reserve address: https://ftmscan.com/address/0xfd1d36995d76c0f75bbe4637c84c06e4a68bbb3a
// Contracts: https://github.com/sturdyfi/sturdy-contracts/blob/main/ftm-contracts.json
// Lending pools: https://ftmscan.com/address/0x06caE399575E3d20cD4B468c8Ef53fAdd2C6aEC8#code
// Docs: https://docs.sturdy.finance/overview/what-is-sturdy
// To find sTokens, use https://ftmscan.com/address/0xc06dc19a4efa1a832f4618ce383d8cb9c7f4d600#readContract getReserveTokensAddresses()

contract LenderStrategy is BaseStrategy {
    using SafeERC20 for IERC20;
    using Address for address;
    using SafeMath for uint256;
    using SafeMath for uint8;

    /* ========== STATE VARIABLES ========== */

    // swap stuff
    address internal constant spookyRouter = address(0xF491e7B69E4244ad4002BC14e878a34207E38c29);
    address public constant wftm = address(0x21be370D5312f44cB42ce377BC9b8a0cEF1A4C83);
    address public constant hnd = address(0x10010078a54396F62c96dF8532dc2B4847d47ED3);
    string internal stratName; // we use this for our strategy's name on cloning

    bool internal forceHarvestTriggerOnce; // only set this to true externally when we want to trigger our keepers to harvest for us
    uint256 public minHarvestCredit; // if we hit this amount of credit, harvest the strategy
    uint256 constant BASIS_PRECISION = 10000;

    MultiStrategyProxy public multiStratProxy;
    address public gauge;
    address public proxy;
    
    CErc20I public cToken;

    uint256 public minIbToSell = 0 ether;
    
    /* ========== CONSTRUCTOR ========== */

    constructor(
        address _vault,
        string memory _name,
        address _multiStratProxy,
        address _gauge,
        address _cToken
    ) BaseStrategy(_vault) {
        _initializeStrat(_name, _multiStratProxy, _gauge, _cToken);
    }

    function initialize(
        address _vault,
        address _strategist,
        address _rewards,
        address _keeper,
        string memory _name,
        address _multiStratProxy,
        address _gauge,
        address _cToken
    ) public {
        _initialize(_vault, _strategist, _rewards, _keeper);
        _initializeStrat(_name, _multiStratProxy, _gauge, _cToken);
    }

    // this is called by our original strategy, as well as any clones
    function _initializeStrat(string memory _name, address _multiStratProxy, address _gauge, address _cToken) internal {
        // initialize variables
        maxReportDelay = 14400; // 4 hours 
        // set our strategy's name
        stratName = _name;
        multiStratProxy = MultiStrategyProxy(_multiStratProxy);
        gauge = _gauge;
        cToken = CErc20I(_cToken);
        want.safeApprove(_cToken, type(uint256).max);
        IERC20(_cToken).safeApprove(address(multiStratProxy.proxy()), type(uint256).max);
        IERC20(_cToken).safeApprove(address(multiStratProxy), type(uint256).max);
        IERC20(hnd).safeApprove(spookyRouter, type(uint256).max);
    }

    function cloneStrategy(
        address _vault,
        address _strategist,
        address _rewards,
        address _keeper,
        string memory _name
    ) external returns (address payable newStrategy) {
        // Copied from https://github.com/optionality/clone-factory/blob/master/contracts/CloneFactory.sol
        bytes20 addressBytes = bytes20(address(this));

        assembly {
            // EIP-1167 bytecode
            let clone_code := mload(0x40)
            mstore(clone_code, 0x3d602d80600a3d3981f3363d3d373d3d3d363d73000000000000000000000000)
            mstore(add(clone_code, 0x14), addressBytes)
            mstore(add(clone_code, 0x28), 0x5af43d82803e903d91602b57fd5bf30000000000000000000000000000000000)
            newStrategy := create(0, clone_code, 0x37)
        }

        LenderStrategy(newStrategy).initialize(_vault, _strategist, _rewards, _keeper, _name, address(multiStratProxy), gauge, address(cToken));

    }

    /* ========== VIEWS ========== */

    function name() external view override returns (string memory) {
        return stratName;
    }

    function balanceOfWant() public view returns (uint256) {
        return want.balanceOf(address(this));
    }

    function balanceOfStaked() public view returns (uint256) {
        uint256 total = multiStratProxy.totalAssets(gauge);
        uint256 totalShares = multiStratProxy.totalSupply(gauge);
        // Assets = shares * total / totalShares
        if(totalShares == 0) {
            return 0;
        }
        uint256 cTokensStaked = multiStratProxy.balanceOf(gauge, address(this)).mul(total).div(totalShares);
        return cTokensStaked.mul(cToken.exchangeRateStored()) / 1e18; // TODO check decimals
    }

    function estimatedTotalAssets() public view override returns (uint256) {
        // look at our staked tokens and any free tokens sitting in the strategy
        return balanceOfStaked().add(balanceOfWant());
    }

    /* ========== MUTATIVE FUNCTIONS ========== */

    function adjustPosition(uint256 _debtOutstanding) internal override {
        if (emergencyExit) {
            return;
        }
        // send all of our want tokens to be deposited
        uint256 toInvest = balanceOfWant();
        // stake only if we have something to stake
        if (toInvest > 0) {
            uint256 balance = want.balanceOf(address(this));
            require(cToken.mint(balance) == 0, "ctoken: mint fail");
            multiStratProxy.deposit(gauge, cToken.balanceOf(address(this)));
        }
    }

    function prepareReturn(uint256 _debtOutstanding)
        internal
        override
        returns (
            uint256 _profit,
            uint256 _loss,
            uint256 _debtPayment
        )
    {
        // Sell HND for want
        uint256 hnd_amount = IERC20(hnd).balanceOf(address(this));
       if(hnd_amount > minIbToSell) {
            address[] memory path = getTokenOutPath(hnd, address(want));    
            IUniswapV2Router02(spookyRouter).swapExactTokensForTokens(hnd_amount, hnd_amount.mul(95).div(100), path, address(this), block.timestamp);
       }
        uint256 assets = estimatedTotalAssets();
        uint256 wantBal = balanceOfWant();

        uint256 debt = vault.strategies(address(this)).totalDebt;
        uint256 amountToFree;

        uint256 stakedBalance = balanceOfStaked();
        
        if (assets >= debt) {
            
            _debtPayment = _debtOutstanding;
            _profit = assets - debt;

            amountToFree = _profit.add(_debtPayment);
            
            if (amountToFree > 0 && wantBal < amountToFree) {
                liquidatePosition(amountToFree);
                
                uint256 newLoose = want.balanceOf(address(this));
                //if we dont have enough money adjust _debtOutstanding and only change profit if needed
                if (newLoose < amountToFree) {
                    if (_profit > newLoose) {
                        _profit = newLoose;
                        _debtPayment = 0;
                    } else {
                        _debtPayment = Math.min(
                            newLoose - _profit,
                            _debtPayment
                        );
                    }
                }
            }
        } else {
            //serious loss should never happen but if it does lets record it accurately
            _loss = debt - assets;
        }

        // we're done harvesting, so reset our trigger if we used it
        forceHarvestTriggerOnce = false;
    }


    function getTokenOutPath(address _token_in, address _token_out) internal pure returns (address[] memory _path) {
        bool is_wftm = _token_in == address(wftm) || _token_out == address(wftm);
        _path = new address[](is_wftm ? 2 : 3);
        _path[0] = _token_in;
        if (is_wftm) {
            _path[1] = _token_out;
        } else {
            _path[1] = address(wftm);
            _path[2] = _token_out;
        }
    }


    function liquidatePosition(uint256 _amountNeeded)
        internal
        override
        returns (uint256 _liquidatedAmount, uint256 _loss)
    {
        uint256 wantAvailable = want.balanceOf(address(this));
        if (_amountNeeded > wantAvailable) {
            uint256 amountToWithdraw = _amountNeeded.sub(wantAvailable);
            uint256 stakedBal = balanceOfStaked();
            uint256 stakePercent = amountToWithdraw.mul(BASIS_PRECISION).div(stakedBal);
            
            // set thresholds to make sure we don't try to withdraw too much or too little 
            stakePercent = Math.max(10, stakePercent);
            
            uint256 withdrawAmt = stakedBal.mul(stakePercent).div(BASIS_PRECISION);
            withdrawAmt = Math.max(withdrawAmt, amountToWithdraw);
            withdrawAmt = Math.min(stakedBal, withdrawAmt);

            uint256 amountCToken = convertFromUnderlying(withdrawAmt);
            multiStratProxy.withdraw(gauge, amountCToken); 
            cToken.redeem(Math.min(amountCToken, cToken.balanceOf(address(this))));

            _liquidatedAmount = balanceOfWant();
        } else {
            _liquidatedAmount = _amountNeeded;
        }
    }

    event DEBU(string s, uint256 x);
    
    function debugConvertFromUnderlying(uint256 amountOfUnderlying) public returns (uint256 balance) {
        if (amountOfUnderlying == 0) {
            balance = 0;
        } else {
            emit DEBU("amountOfUnderlying", amountOfUnderlying);
            // 1cToken = 1 underlying * exchangeRateStored
            balance = amountOfUnderlying.mul(1e18).div(cToken.exchangeRateStored());
            emit DEBU("result", balance);
            emit DEBU("exchangeRate", cToken.exchangeRateStored());

        }
    }

    function convertFromUnderlying(uint256 amountOfUnderlying) public view returns (uint256 balance) {
        if (amountOfUnderlying == 0) {
            balance = 0;
        } else {
            balance = amountOfUnderlying.mul(1e18).div(cToken.exchangeRateStored());
        }
    }

    function liquidateAllPositions() internal override returns (uint256) {
        uint256 stakedBalance = balanceOfStaked();
        uint256 amountCToken = convertFromUnderlying(stakedBalance);
        multiStratProxy.withdraw(gauge, amountCToken); 
        cToken.redeem(Math.min(amountCToken, cToken.balanceOf(address(this))));
        return balanceOfWant();
    }

    function prepareMigration(address _newStrategy) internal override {
        liquidateAllPositions();
    }


    function protectedTokens()
        internal
        view
        override
        returns (address[] memory)
    {
        //want, aToken
        address[] memory protected = new address[](1);
        protected[0] = address(cToken);
        return protected;
    }

    // our main trigger is regarding our DCA since there is low liquidity for our emissionToken
    function harvestTrigger(uint256 callCostinEth)
        public
        view
        override
        returns (bool)
    {
        StrategyParams memory params = vault.strategies(address(this));

        // harvest no matter what once we reach our maxDelay
        if (block.timestamp.sub(params.lastReport) > maxReportDelay) {
            return true;
        }

        // trigger if we want to manually harvest
        if (forceHarvestTriggerOnce) {
            return true;
        }

        // trigger if we have enough credit
        if (vault.creditAvailable() >= minHarvestCredit) {
            return true;
        }

        // otherwise, we don't harvest
        return false;
    }

    function ethToWant(uint256 _amtInWei)
        public
        view
        override
        returns (uint256)
    {}

    /* ========== SETTERS ========== */

    ///@notice This allows us to manually harvest with our keeper as needed
    function setForceHarvestTriggerOnce(bool _forceHarvestTriggerOnce)
        external
        onlyAuthorized
    {
        forceHarvestTriggerOnce = _forceHarvestTriggerOnce;
    }

    ///@notice When our strategy has this much credit, harvestTrigger will be true.
    function setMinHarvestCredit(uint256 _minHarvestCredit)
        external
        onlyAuthorized
    {
        minHarvestCredit = _minHarvestCredit;
    }

    receive() external payable {}

}