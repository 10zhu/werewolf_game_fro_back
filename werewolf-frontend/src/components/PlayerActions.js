import React, { useState } from 'react';
export const PlayerActions = ({ gamePhase, onSubmitAction, players, currentPlayer }) => {
  const [selectedAction, setSelectedAction] = useState('');
  const [targetPlayer, setTargetPlayer] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    if (selectedAction) {
      // For run_for_policeman, automatically set target as current player
      const target = selectedAction === 'run_for_policeman' ? currentPlayer : targetPlayer;
      onSubmitAction(selectedAction, target);
      setSelectedAction('');
      setTargetPlayer('');
    }
  };

  const actions = {
    NIGHT: ['kill', 'check', 'heal', 'poison', 'sleep'],
    DAY: ['vote'],
    POLICEMAN_SELECTION: ['run_for_policeman', 'vote_policeman'],
  };

  const getAvailableActions = () => {
    if (gamePhase === 'POLICEMAN_SELECTION') {
      // Check if current player is already a candidate
      const isCandidate = players.find(p => p.player_id === currentPlayer)?.running_for_policeman;
      if (isCandidate) {
        return []; // Candidates cannot vote
      }
      const candidates = players.filter(p => p.running_for_policeman);
      if (candidates.length > 0) {
        return ['vote_policeman'];
      }
      return ['run_for_policeman'];
    }
    return actions[gamePhase] || [];
  };

  return (
    <div className="bg-white p-4 rounded-lg shadow">
      <h2 className="text-xl font-semibold mb-4">Actions</h2>

      {gamePhase === 'POLICEMAN_SELECTION' && (
        <div className="mb-6 bg-gray-50 p-4 rounded-lg">
          <h3 className="text-lg font-semibold mb-3">Policeman Candidates:</h3>
          {players.some(p => p.running_for_policeman) ? (
            <div className="space-y-3">
              {players
                .filter(p => p.running_for_policeman)
                .map(candidate => (
                  <div key={candidate.player_id}
                       className="p-3 bg-white rounded-lg shadow-sm border border-gray-200">
                    <p className="font-medium">Player {candidate.position}</p>
                    <p className="text-sm text-gray-600">Click vote action to support this candidate</p>
                  </div>
                ))}
            </div>
          ) : (
            <p className="text-gray-600 italic">
              No candidates yet. Choose 'run_for_policeman' if you want to be a candidate.
            </p>
          )}
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block mb-2">Action:</label>
          <select
            value={selectedAction}
            onChange={(e) => setSelectedAction(e.target.value)}
            className="w-full p-2 border rounded"
          >
            <option value="">Select action</option>
            {getAvailableActions().map((action) => (
              <option key={action} value={action}>
                {action}
              </option>
            ))}
          </select>
        </div>

        {selectedAction && (
          <div>
            <label className="block mb-2">Target:</label>
            <select
              value={targetPlayer}
              onChange={(e) => setTargetPlayer(e.target.value)}
              className="w-full p-2 border rounded"
            >
              <option value="">Select target</option>
              {players
                .filter(player => {
                  if (selectedAction === 'vote_policeman') {
                    return player.running_for_policeman;
                  }
                  if (selectedAction === 'run_for_policeman') {
                    return player.player_id === currentPlayer;
                  }
                  return true;
                })
                .map((player) => (
                  <option key={player.player_id} value={player.player_id}>
                     Player {parseInt(player.player_id.replace('p', '')) + 1}
                  </option>
                ))}
            </select>
          </div>
        )}

        <button
          type="submit"
          className="bg-blue-500 text-white px-4 py-2 rounded w-full"
          disabled={!selectedAction || !targetPlayer}
        >
          Submit Action
        </button>
      </form>
    </div>
  );
};