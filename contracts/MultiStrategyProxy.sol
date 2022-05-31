// SPDX-License-Identifier: MIT
pragma solidity ^0.8.11;

import "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import "@openzeppelin/contracts/utils/math/SafeMath.sol";
import "@openzeppelin/contracts/proxy/utils/Initializable.sol";
import { IGauge, IFeeDistribution } from "./interfaces/curve.sol";
import { SafeProxy, IProxy } from "./interfaces/proxy.sol";


contract MultiStrategyProxy is Initializable {
    using SafeERC20 for IERC20;
    using Address for address;
    using SafeMath for uint256;
    using SafeProxy for IProxy;

    struct Strategy {
        address addr;
        uint256 shares;
        bool isPaused; // Indicates deposits are paused for this strategy
    }

    IProxy public proxy;
    address public minter;
    address public hnd;
    address public gaugeController;
    address public governance;
    address public pendingGovernance;
    address public feeDistribution;// = FeeDistribution(0xA464e6DCda8AC41e03616F95f4BC98a13b8922Dc);
    uint256 dust = 1e12;

    mapping(address => Strategy[]) strategies;
    mapping(address => uint256) totalSupply;
    mapping(address => bool) public voters;

    // EVENTS
    event StrategyApproved(address indexed _gauge, address indexed _strategy);
    event StrategyRevoked(address indexed _gauge, address indexed _strategy);
    event StrategyPaused(address indexed _gauge, address indexed _strategy);
    event StrategyUnpaused(address indexed _gauge, address indexed _strategy);
    event Transfer(address indexed _gauge, address indexed from, address indexed to, uint256 value);

    uint256 lastTimeCursor;

    constructor() {
        governance = msg.sender;
    }

    function initialize(
        address _gov,
        address _proxy
    ) public initializer {
        governance = _gov;
        proxy = IProxy(_proxy);
        hnd = address(0x10010078a54396F62c96dF8532dc2B4847d47ED3);
        minter = address(0x42B458056f887Fd665ed6f160A59Afe932e1F559);
        gaugeController = address(0x89Aa51685a2B658be8a7b9C3Af70D66557544181);
    }

    function setGovernance(address _governance) external {
        require(msg.sender == governance, "!governance");
        pendingGovernance = _governance;
    }

    function setDust(uint256 _dust) external {
        require(msg.sender == governance, "!governance");
        dust = _dust;
    }

    function acceptGovernance() external {
        require(msg.sender == pendingGovernance, "!pendingGovernance");
        governance = pendingGovernance;
        pendingGovernance = address(0);
    }

    function findStrategy(address _gauge, address _strategy) public view returns (uint256) {
        Strategy[] storage strats = strategies[_gauge];
        for (uint i; i < strats.length; i++) {
            if (strats[i].addr == _strategy)
                return i;
        }
        return type(uint256).max;
    }

    function approveStrategy(address _gauge, address _strategy) external {
        require(msg.sender == governance, "!governance");
        uint256 idx = findStrategy(_gauge, _strategy);
        require (idx == type(uint256).max, "Strategy already approved");
        strategies[_gauge].push(Strategy(_strategy, 0, false));
        emit StrategyApproved(_gauge, _strategy);           
    }

    function revokeStrategy(address _gauge, address _strategy, bool _force) external {
        require(msg.sender == governance, "!governance");
        uint256 idx = findStrategy(_gauge, _strategy);
        require (idx == type(uint256).max, "Strategy not found");
        require (strategies[_gauge][idx].shares == 0 || _force, "Strategy balance non-zero");
        strategies[_gauge][idx] = strategies[_gauge][strategies[_gauge].length];
        strategies[_gauge].pop();
    }

    function pauseStrategy(address _gauge, address _strategy) external {
        require(msg.sender == governance, "!governance");
        uint256 idx = findStrategy(_gauge, _strategy);
        require (idx == type(uint256).max, "Strategy not found");
        require (!strategies[_gauge][idx].isPaused, "Strategy already paused");
        strategies[_gauge][idx].isPaused = true;
        emit StrategyPaused(_gauge, _strategy);           
    }

    function unpauseStrategy(address _gauge, address _strategy) external {
        require(msg.sender == governance, "!governance");
        uint256 idx = findStrategy(_gauge, _strategy);
        require (idx != type(uint256).max, "Strategy not found");
        require (strategies[_gauge][idx].isPaused, "Strategy not paused");
        strategies[_gauge][idx].isPaused = false;
        emit StrategyUnpaused(_gauge, _strategy);           
    }

    function approveVoter(address _voter) external {
        require(msg.sender == governance, "!governance");
        voters[_voter] = true;
    }

    function revokeVoter(address _voter) external {
        require(msg.sender == governance, "!governance");
        voters[_voter] = false;
    }

    function lock() external {
        uint256 amount = IERC20(hnd).balanceOf(address(proxy));
        if (amount > 0) proxy.increaseAmount(amount);
    }

    function vote(address _gauge, uint256 _amount) public {
        require(voters[msg.sender], "!voter");
        proxy.safeExecute(gaugeController, 0, abi.encodeWithSignature("vote_for_gauge_weights(address,uint256)", _gauge, _amount));
    }

    function totalAssets(address _gauge) public view returns (uint256) {
        return IERC20(_gauge).balanceOf(address(proxy));
    }

    function convertToShares(address _gauge, uint256 assets) public view returns (uint256) {
        uint256 _totalSupply = totalSupply[_gauge];
        uint256 _totalAssets = totalAssets(_gauge);
        if (_totalAssets == 0 || _totalSupply == 0) return assets;
        return assets * _totalSupply / _totalAssets;
    }

    function deposit(address _gauge, uint256 _assets) external {
        // Strategy must be approved
        address strategy = msg.sender;
        uint256 idx = findStrategy(_gauge, strategy);
        require (idx != type(uint256).max, "!strategy");
        require (!strategies[_gauge][idx].isPaused, "!paused"); 

        // require(strategies[_gauge][msg.sender].isApproved, "!strategy");
        // Transfer the LP token from the strategy to the proxy
        address lpToken = IGauge(_gauge).lp_token();
        uint256 shares = convertToShares(_gauge, _assets);
        uint256 balBefore = IERC20(lpToken).balanceOf(address(proxy));
        IERC20(lpToken).transferFrom(msg.sender, address(proxy), _assets);
        require(IERC20(lpToken).balanceOf(address(proxy)) - balBefore == _assets);

        // Need to harvest before minting
        _harvest(_gauge);

        // Mint shares for the strategy
        _mint(_gauge, idx, shares);
        
        // Now deposit into gauge
        proxy.safeExecute(lpToken, 0, abi.encodeWithSignature("approve(address,uint256)", _gauge, 0));
        proxy.safeExecute(lpToken, 0, abi.encodeWithSignature("approve(address,uint256)", _gauge, _assets));
        proxy.safeExecute(_gauge, 0, abi.encodeWithSignature("deposit(uint256)", _assets));
    }

    function _withdraw(
        address _gauge,
        uint256 _assets,
        address _strategy
    ) internal returns (uint256) {
        address lpToken = IGauge(_gauge).lp_token();
        uint256 shares = convertToShares(_gauge, _assets);

        uint256 idx = findStrategy(_gauge, _strategy);
        require (idx != type(uint256).max, "!strategy");

        // check the strategy has enough balance
        require (strategies[_gauge][idx].shares >= shares);
        
        // Need to harvest before burning
        _harvest(_gauge);

        // burn the shares
        _burn(_gauge, idx, shares);

        // withdraw lp tokens from the gauge
        uint256 _balance = IERC20(lpToken).balanceOf(address(proxy));
        proxy.safeExecute(_gauge, 0, abi.encodeWithSignature("withdraw(uint256)", _assets));
        _balance = IERC20(lpToken).balanceOf(address(proxy)).sub(_balance);
        proxy.safeExecute(lpToken, 0, abi.encodeWithSignature("transfer(address,uint256)", msg.sender, _balance));
        return _balance;
    }

    function balanceOf(address _gauge, address _strategy) public view returns (uint256) {
        uint256 idx = findStrategy(_gauge, _strategy);
        require (idx != type(uint256).max, "!strategy");
        return strategies[_gauge][idx].shares;
    }

    //
    function withdrawAll(address _gauge) external returns (uint256) {
        //TODO require GOV / strategy!
        return _withdraw(_gauge, balanceOf(_gauge, msg.sender), msg.sender);
    }

    // 
    function withdraw(address _gauge, uint256 _assets) internal returns (uint256) {
        //TODO require GOV / strategy!
        return _withdraw(_gauge, _assets, msg.sender);
    }

    function _harvest(address _gauge) internal {
        uint256 before = IERC20(hnd).balanceOf(address(proxy));
        proxy.safeExecute(minter, 0, abi.encodeWithSignature("mint(address)", _gauge));
        uint256 harvested = (IERC20(hnd).balanceOf(address(proxy))).sub(before);

        if (harvested > dust) {
            _distributeHarvest(_gauge, harvested);
        }
    }

    function harvest(address _gauge) external {
        _harvest(_gauge);
    }

    function _distributeHarvest(address _gauge, uint256 _amount) internal {
        Strategy[] storage strats = strategies[_gauge];
        for (uint i; i < strats.length; i++) {
            if (strats[i].shares > 0) {
                uint256 amount = strats[i].shares.mul(_amount).div(totalSupply[_gauge]);
                proxy.safeExecute(hnd, 0, abi.encodeWithSignature("transfer(address,uint256)", msg.sender, amount));
            }
        }
    }

    function setfeeDistribution(address _feeDistribution) external {
        require(msg.sender == governance, "!gov");
        feeDistribution = _feeDistribution;
    }

    // veHND holders do not currently share in fee revenue. 
    // Putting this as a placehold if they do in the future
    function claimVeHNDRewards(address recipient) external {
        require(msg.sender == governance, "!gov");
        if (block.timestamp < lastTimeCursor.add(604800)) return;

        address p = address(proxy);
        IFeeDistribution(feeDistribution).claim_many([p, p, p, p, p, p, p, p, p, p, p, p, p, p, p, p, p, p, p, p]);
        lastTimeCursor = IFeeDistribution(feeDistribution).time_cursor_of(address(proxy));
    }

    function sweep(address _token) external {
        require(msg.sender == governance, "!gov");
        IERC20(_token).safeTransfer(governance, IERC20(_token).balanceOf(address(this)));
    }

    function sweepProxy(address _token) external {
        require(msg.sender == governance, "!gov");
        proxy.safeExecute(_token, 0, abi.encodeWithSignature("transfer(address,uint256)", governance, IERC20(_token).balanceOf(address(proxy))));
    }

    function _mint(address _gauge, uint256 _idx, uint256 _shares) internal {
        totalSupply[_gauge] += _shares;
        strategies[_gauge][_idx].shares += _shares;
        emit Transfer(_gauge, address(0), strategies[_gauge][_idx].addr, _shares);       
    }

    function _burn(address _gauge, uint256 _idx, uint256 _shares) internal {
        uint256 strategyBalance = strategies[_gauge][_idx].shares;
        require(strategyBalance >= _shares, "burn amount exceeds balance");
        unchecked {
            strategies[_gauge][_idx].shares = strategyBalance - _shares;
        }
        totalSupply[_gauge] -= _shares;
        emit Transfer(_gauge, strategies[_gauge][_idx].addr, address(0), _shares);
    }

    function claimRewards(address _gauge, address _token) external {
        require(governance == msg.sender, "!governance");
        IGauge(_gauge).claim_rewards(address(proxy));
        proxy.safeExecute(_token, 0, abi.encodeWithSignature("transfer(address,uint256)", msg.sender, IERC20(_token).balanceOf(address(proxy))));
    }

    event DEBU(string s, uint256 x);
    function debu(address _gauge) external {
        uint256 before = IERC20(hnd).balanceOf(address(proxy));
        proxy.safeExecute(minter, 0, abi.encodeWithSignature("mint(address)", _gauge));
        uint256 harvested = (IERC20(hnd).balanceOf(address(proxy))).sub(before);

        emit DEBU("HND BALANCE ", IERC20(hnd).balanceOf(address(proxy)));
        emit DEBU("HARVESTED ", harvested);
    }
}