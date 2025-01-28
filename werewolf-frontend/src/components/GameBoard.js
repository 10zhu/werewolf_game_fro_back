//// src/components/GameBoard.js
import React from 'react';

export const GameBoard = ({ players, currentPlayer, gamePhase }) => {
  console.log("GameBoard props:", { players, currentPlayer, gamePhase }); // Debug log

  if (!Array.isArray(players)) {
    console.warn("Players prop is not an array:", players);
    return <div>Invalid players data</div>;
  }

  if (players.length === 0) {
    return <div className="bg-white p-4 rounded-lg shadow mb-4">
      <h2 className="text-xl font-semibold mb-4">Players</h2>
      <p>Loading players data...</p>
    </div>;
  }

  const currentPlayerData = players.find(p => p.player_id === currentPlayer);
  console.log("Current player data:", currentPlayerData); // Debug log

  return (
    <div className="bg-white p-4 rounded-lg shadow mb-4">
      {currentPlayerData && (
        <div className="mb-6 p-4 bg-blue-100 rounded-lg">
          <h3 className="text-lg font-semibold mb-2">Your Role</h3>
          <p className="text-xl font-bold text-blue-800">{currentPlayerData.role}</p>
          <p className="text-sm mt-2">
            {getRoleDescription(currentPlayerData.role)}
          </p>
        </div>
      )}

      <h2 className="text-xl font-semibold mb-4">All Players</h2>
      <div className="grid grid-cols-3 gap-4">
        {players.map((player) => (
          <div
            key={player.player_id}
            className={`p-4 rounded ${
              player.player_id === currentPlayer
                ? 'bg-blue-100'
                : 'bg-gray-100'
            }`}
          >
            <p className="font-semibold">Position {parseInt(player.player_id.replace('p', ''))+1}</p>
            <p>Status: {player.status}</p>
            {player.player_id === currentPlayer && (
              <p className="font-bold text-blue-600">Role: {player.role}</p>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};

const getRoleDescription = (role) => {
  const descriptions = {
    'WEREWOLF': 'Each night, work with other werewolves to choose a victim.',
    'VILLAGER': 'Work with other villagers to identify and eliminate the werewolves.',
    'SEER': 'Each night, you can check one player to learn if they are a werewolf.',
    'WITCH': 'You have one healing potion and one poison potion to use during the game.',
    'HUNTER': 'If you die, you can immediately shoot another player.',
    'IDIOT': 'If voted out, you remain alive but lose voting rights.'
  };
  return descriptions[role] || 'No description available';
};

//import React from 'react';
//
//export const GameBoard = ({ players, currentPlayer, gamePhase }) => {
//  const currentPlayerData = players.find(p => p.player_id === currentPlayer);
//
//  return (
//    <div className="bg-white p-4 rounded-lg shadow mb-4">
//      {/* Show current player's role prominently */}
//      {currentPlayerData && (
//        <div className="mb-6 p-4 bg-blue-100 rounded-lg">
//          <h3 className="text-lg font-semibold mb-2">Your Role</h3>
//          <p className="text-xl font-bold text-blue-800">{currentPlayerData.role}</p>
//          <p className="text-sm mt-2">
//            {getRoleDescription(currentPlayerData.role)}
//          </p>
//        </div>
//      )}
//
//      <h2 className="text-xl font-semibold mb-4">Players</h2>
//      <div className="grid grid-cols-3 gap-4">
//        {players.map((player) => (
//          <div
//            key={player.player_id}
//            className={`p-4 rounded ${
//              player.player_id === currentPlayer
//                ? 'bg-blue-100'
//                : 'bg-gray-100'
//            }`}
//          >
//            <p className="font-semibold">Position {parseInt(player.player_id.replace('p', '')) + 1}</p>
//            <p>Status: {player.status}</p>
//            {/* Only show role for current player */}
//            {player.player_id === currentPlayer && <p>Role: {player.role}</p>}
//          </div>
//        ))}
//      </div>
//    </div>
//  );
//};
//
//// Helper function to get role descriptions
//const getRoleDescription = (role) => {
//  const descriptions = {
//    'WEREWOLF': 'Each night, work with other werewolves to choose a victim.',
//    'VILLAGER': 'Work with other villagers to identify and eliminate the werewolves.',
//    'SEER': 'Each night, you can check one player to learn if they are a werewolf.',
//    'WITCH': 'You have one healing potion and one poison potion to use during the game.',
//    'HUNTER': 'If you die, you can immediately shoot another player.',
//    'IDIOT': 'If voted out, you remain alive but lose voting rights.'
//  };
//  return descriptions[role] || 'No description available';
//};