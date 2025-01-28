// src/components/GameLobby.js
import React from 'react';

export const GameLobby = ({ players, onSelectPlayer, onStartGame, currentPlayer }) => (
  <div className="bg-white p-4 rounded-lg shadow mb-4">
    <h2 className="text-xl font-semibold mb-4">Game Lobby</h2>

    {/* Player selection */}
    <div className="mb-4">
      <h3 className="text-lg font-medium mb-2">Select your position:</h3>
      <div className="grid grid-cols-3 gap-4 mb-4">
        {Array.from({length: 12}).map((_, index) => (
          <button
            key={`p${index}`}
            onClick={() => onSelectPlayer(`p${index}`)}
            className={`p-4 rounded-lg transition-colors ${
              currentPlayer === `p${index}`
                ? 'bg-blue-500 text-white'
                : 'bg-gray-100 hover:bg-gray-200'
            }`}
          >
            Position {index + 1}
          </button>
        ))}
      </div>
    </div>

    {/* Show confirmation message when player is selected */}
    {currentPlayer && (
      <div className="mb-4 p-4 bg-green-100 rounded-lg">
        <p className="text-green-800">You have selected Position {parseInt(currentPlayer.replace('p', '')) + 1}</p>
        <p className="text-sm text-green-600">Your role will be revealed when the game starts!</p>
      </div>
    )}

    <button
      onClick={onStartGame}
      disabled={!currentPlayer}
      className={`px-4 py-2 rounded ${
        currentPlayer
          ? 'bg-green-500 text-white hover:bg-green-600'
          : 'bg-gray-300 cursor-not-allowed'
      }`}
    >
      {currentPlayer ? 'Start Game' : 'Select your position to start'}
    </button>
  </div>
);