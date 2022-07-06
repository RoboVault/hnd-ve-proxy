// SPDX-License-Identifier: MIT
pragma solidity ^0.8.11;

import "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import "@openzeppelin/contracts/utils/math/SafeMath.sol";
import "@openzeppelin/contracts/proxy/utils/Initializable.sol";
import { IGauge, IFeeDistribution } from "./interfaces/curve.sol";
import { SafeProxy, IProxy } from "./interfaces/IProxy.sol";

contract StrategyProxy is Initializable {
    using SafeERC20 for IERC20;
    using Address for address;
    using SafeMath for uint256;
    using SafeProxy for IProxy;

    IProxy public proxy;
    address public minter;
    address public hnd;
    address public gaugeController;
    address public governance;
    address public pendingGovernance;
    address public feeDistribution;// = FeeDistribution(0xA464e6DCda8AC41e03616F95f4BC98a13b8922Dc);

    mapping(address => address) public strategies;
    mapping(address => bool) public voters;

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
        strategies[_gauge] = _strategy;
    }

    function revokeStrategy(address _gauge) external {
        require(msg.sender == governance, "!governance");
        strategies[_gauge] = address(0);
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
        require(msg.sender == governance, "!governance");
        uint256 amount = IERC20(hnd).balanceOf(address(proxy));
        if (amount > 0) proxy.increaseAmount(amount);
    }

    function vote(address _gauge, uint256 _amount) public {
        require(voters[msg.sender], "!voter");
        proxy.safeExecute(gaugeController, 0, abi.encodeWithSignature("vote_for_gauge_weights(address,uint256)", _gauge, _amount));
    }

    function withdraw(
        address _gauge,
        address _token,
        uint256 _amount
    ) public returns (uint256) {
        require(strategies[_gauge] == msg.sender, "!strategy");
        uint256 _balance = IERC20(_token).balanceOf(address(proxy));
        
        proxy.safeExecute(_gauge, 0, abi.encodeWithSignature("withdraw(uint256)", _amount));
        _balance = IERC20(_token).balanceOf(address(proxy)).sub(_balance);
        proxy.safeExecute(_token, 0, abi.encodeWithSignature("transfer(address,uint256)", msg.sender, _balance));
        return _balance;
    }

    function balanceOf(address _gauge) public view returns (uint256) {
        return IERC20(_gauge).balanceOf(address(proxy));
    }

    function withdrawAll(address _gauge, address _token) external returns (uint256) {
        require(strategies[_gauge] == msg.sender, "!strategy");
        return withdraw(_gauge, _token, balanceOf(_gauge));
    }

    function deposit(address _gauge, address _token) external {
        require(strategies[_gauge] == msg.sender, "!strategy");
        uint256 _balance = IERC20(_token).balanceOf(address(this));
        IERC20(_token).safeTransfer(address(proxy), _balance);
        _balance = IERC20(_token).balanceOf(address(proxy));

        proxy.safeExecute(_token, 0, abi.encodeWithSignature("approve(address,uint256)", _gauge, 0));
        proxy.safeExecute(_token, 0, abi.encodeWithSignature("approve(address,uint256)", _gauge, _balance));
        proxy.safeExecute(_gauge, 0, abi.encodeWithSignature("deposit(uint256)", _balance));
    }

    function harvest(address _gauge) external {
        require(strategies[_gauge] == msg.sender, "!strategy");
        uint256 _balance = IERC20(hnd).balanceOf(address(proxy));
        proxy.safeExecute(minter, 0, abi.encodeWithSignature("mint(address)", _gauge));
        _balance = (IERC20(hnd).balanceOf(address(proxy))).sub(_balance);
        proxy.safeExecute(hnd, 0, abi.encodeWithSignature("transfer(address,uint256)", msg.sender, _balance));
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

    function claimRewards(address _gauge, address _token) external {
        require(strategies[_gauge] == msg.sender, "!strategy");
        IGauge(_gauge).claim_rewards(address(proxy));
        proxy.safeExecute(_token, 0, abi.encodeWithSignature("transfer(address,uint256)", msg.sender, IERC20(_token).balanceOf(address(proxy))));
    }
}