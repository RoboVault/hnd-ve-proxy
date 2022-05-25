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
        bool isInitialised;
        bool isApproved;
        uint256 shares;
    }

    IProxy public proxy;
    address public minter;
    address public hnd;
    address public gaugeController;
    address public governance;
    address public pendingGovernance;
    address public feeDistribution;// = FeeDistribution(0xA464e6DCda8AC41e03616F95f4BC98a13b8922Dc);

    // gauge => strategies
    mapping(address => mapping(address => Strategy)) strategies;

    // Total shares for a given gauge
    mapping(address => uint256) totalSupply;

    
    mapping(address => bool) public voters;

    // EVENTS
    event StrategyApproved(address indexed _gauge, address indexed _strategy);
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

    function acceptGovernance() external {
        require(msg.sender == pendingGovernance, "!pendingGovernance");
        governance = pendingGovernance;
        pendingGovernance = address(0);
    }

    function approveStrategy(address _gauge, address _strategy) external {
        require(msg.sender == governance, "!governance");

        // Check it's a fresh strat, and approve it if it is. Initials with a balance of 0 shares
        if (!strategies[_gauge][_strategy].isInitialised) {
            strategies[_gauge][_strategy] = Strategy(true, true, 0);
            emit StrategyApproved(_gauge, _strategy);
            return;
        }

        // Check it's not already approved
        require (!strategies[_gauge][_strategy].isApproved, 'isApproved');

        // approve the strat
        strategies[_gauge][_strategy].isApproved = true;
        emit StrategyApproved(_gauge, _strategy);           
    }

    function revokeStrategy(address _gauge, address _strategy) external {
        require(msg.sender == governance, "!governance");
        require (strategies[_gauge][_strategy].isApproved, '!approved');
        strategies[_gauge][_strategy].isApproved = false;
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
        require(strategies[_gauge][msg.sender].isApproved, "!strategy");
        address strategy = msg.sender;

        // Transfer the LP token from the strategy to the proxy
        address lpToken = IGauge(_gauge).lp_token();
        uint256 shares = convertToShares(_gauge, _assets);
        uint256 balBefore = IERC20(lpToken).balanceOf(address(proxy));
        IERC20(lpToken).transferFrom(msg.sender, address(proxy), _assets);
        require(IERC20(lpToken).balanceOf(address(proxy)) - balBefore == _assets);

        // Mint shares for the strategy
        _mint(_gauge, strategy, shares);
        
        // Now deposit into gauge
        proxy.safeExecute(lpToken, 0, abi.encodeWithSignature("approve(address,uint256)", _gauge, 0));
        proxy.safeExecute(lpToken, 0, abi.encodeWithSignature("approve(address,uint256)", _gauge, _assets));
        proxy.safeExecute(_gauge, 0, abi.encodeWithSignature("deposit(uint256)", _assets));
    }

    function withdraw(
        address _gauge,
        uint256 _assets
    ) public returns (uint256) {
        address strategy = msg.sender;
        address lpToken = IGauge(_gauge).lp_token();
        uint256 shares = convertToShares(_gauge, _assets);

        // check the strategy has enough balance
        require (balanceOf(_gauge, strategy) >= shares);
        
        // burn the shares
        _burn(_gauge, strategy, shares);

        // Withdraw lp tokens from the gauge
        uint256 _balance = IERC20(lpToken).balanceOf(address(proxy));
        proxy.safeExecute(_gauge, 0, abi.encodeWithSignature("withdraw(uint256)", _assets));
        _balance = IERC20(lpToken).balanceOf(address(proxy)).sub(_balance);
        proxy.safeExecute(lpToken, 0, abi.encodeWithSignature("transfer(address,uint256)", msg.sender, _balance));
        return _balance;
    }

    function balanceOf(address _gauge, address _strategy) public view returns (uint256) {
        return strategies[_gauge][_strategy].shares;
    }

    // function withdrawAll(address _gauge, address _token) external returns (uint256) {
    //     require(strategies[_gauge] == msg.sender, "!strategy");
    //     return withdraw(_gauge, _token, balanceOf(_gauge));
    // }

    // function harvest(address _gauge) external {
    //     require(strategies[_gauge] == msg.sender, "!strategy");
    //     uint256 _balance = IERC20(hnd).balanceOf(address(proxy));
    //     proxy.safeExecute(minter, 0, abi.encodeWithSignature("mint(address)", _gauge));
    //     _balance = (IERC20(hnd).balanceOf(address(proxy))).sub(_balance);
    //     proxy.safeExecute(hnd, 0, abi.encodeWithSignature("transfer(address,uint256)", msg.sender, _balance));
    // }

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

    function _mint(address _gauge, address _strategy, uint256 _shares) internal {
        require(_strategy != address(0), "mint to the zero address");
        require(strategies[_gauge][_strategy].isApproved, "minting an unapproved strategy");

        totalSupply[_gauge] += _shares;
        strategies[_gauge][_strategy].shares += _shares;
        emit Transfer(_gauge, address(0), _strategy, _shares);       
    }


    function _burn(address _gauge, address _strategy, uint256 _shares) internal virtual {
        require(_strategy != address(0), "burn from the zero address");

        uint256 strategyBalance = strategies[_gauge][_strategy].shares;
        require(strategyBalance >= _shares, "burn amount exceeds balance");
        unchecked {
            strategies[_gauge][_strategy].shares = strategyBalance - _shares;
        }
        totalSupply[_gauge] -= _shares;
        emit Transfer(_gauge, _strategy, address(0), _shares);
    }

    // function claimRewards(address _gauge, address _token) external {
    //     require(strategies[_gauge] == msg.sender, "!strategy");
    //     IGauge(_gauge).claim_rewards(address(proxy));
    //     proxy.safeExecute(_token, 0, abi.encodeWithSignature("transfer(address,uint256)", msg.sender, IERC20(_token).balanceOf(address(proxy))));
    // }
}