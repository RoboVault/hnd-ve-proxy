// SPDX-License-Identifier: MIT
pragma solidity ^0.8.11;

import "@openzeppelin/contracts/utils/math/SafeMath.sol";
import "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import "@openzeppelin/contracts/proxy/utils/Initializable.sol";

interface VoteEscrow {
  function create_lock(uint, uint) external;
  function increase_amount(uint) external;
  function withdraw() external;
}

contract veHNDVoter is Initializable {
    using SafeERC20 for IERC20;
    using Address for address;
    using SafeMath for uint256;
    
    address public governance;
    address public hnd;
    address public escrow;
    address public strategy;
    address public pendingGovernance;

    function initialize(
        address _gov
    ) public initializer {
        governance = _gov;
        hnd = address(0x10010078a54396F62c96dF8532dc2B4847d47ED3);
        escrow = address(0x376020c5B0ba3Fd603d7722381fAA06DA8078d8a);
    }
    
    function getName() external pure returns (string memory) {
        return "veHNDVoter";
    }
    
    function setStrategy(address _strategy) external {
        require(msg.sender == governance, "!governance");
        strategy = _strategy;
    }
    
    function withdraw(IERC20 _asset) external returns (uint balance) {
        require(msg.sender == strategy, "!strategy");
        balance = _asset.balanceOf(address(this));
        _asset.safeTransfer(strategy, balance);
    }
    
    function createLock(uint _value, uint _unlockTime) external {
        require(msg.sender == strategy || msg.sender == governance, "!authorized");
        IERC20(hnd).safeApprove(escrow, 0);
        IERC20(hnd).safeApprove(escrow, _value);
        VoteEscrow(escrow).create_lock(_value, _unlockTime);
    }
    
    function increaseAmount(uint _value) external {
        require(msg.sender == strategy || msg.sender == governance, "!authorized");
        IERC20(hnd).safeApprove(escrow, 0);
        IERC20(hnd).safeApprove(escrow, _value);
        VoteEscrow(escrow).increase_amount(_value);
    }
    
    function release() external {
        require(msg.sender == strategy || msg.sender == governance, "!authorized");
        VoteEscrow(escrow).withdraw();
    }
    
    function setGovernance(address _governance) external {
        require(msg.sender == governance, "!authorized");
        pendingGovernance = _governance;
    }
    
    function acceptGovernance() external {
        require(msg.sender == pendingGovernance, "!authorized");
        governance = pendingGovernance;
        pendingGovernance = address(0);
    }
    
    function execute(address to, uint value, bytes calldata data) external returns (bool, bytes memory) {
        require(msg.sender == strategy || msg.sender == governance, "!authorized");
        (bool success, bytes memory result) = to.call{value:value}(data);

        return (success, result);
    }
}