import React, { useState, useEffect } from 'react';

export const PlayerActions = ({ gamePhase, onSubmitAction, players, currentPlayer, playerRole }) => {
  const [selectedAction, setSelectedAction] = useState('');
  const [targetPlayer, setTargetPlayer] = useState('');

  // Add debug logging
  useEffect(() => {
    console.log('PlayerActions - Current phase:', gamePhase);
    console.log('PlayerActions - Current player:', currentPlayer);
    console.log('PlayerActions - Available players:', players);
    console.log('PlayerActions - Player Role:', playerRole);
  }, [gamePhase, currentPlayer, players, playerRole]);

  // Reset state when game phase changes
  useEffect(() => {
    setSelectedAction('');
    setTargetPlayer('');
  }, [gamePhase]);

  const handleSubmit = (e) => {
    e.preventDefault();

    // Log action submission
    console.log('Submitting action:', {
      phase: gamePhase,
      action: selectedAction,
      target: targetPlayer
    });

    // Determine the appropriate action
    if (gamePhase === 'POLICEMAN_SELECTION') {
      // Get candidates running for policeman
    const candidates = players.filter(p => p.running_for_policeman);
    console.log('Current policeman candidates:', candidates);

    // Check if current player is already running
    const isCurrentPlayerRunning = candidates.some(c => c.player_id === currentPlayer);
    console.log('Is current player running?', isCurrentPlayerRunning);

    if (isCurrentPlayerRunning) {
      // If current player is running, they can only see that they're a candidate
      return [];
    } else {
      // If candidates exist, allow voting
      if (candidates.length > 0) {
        return ['run_for_policeman', 'vote_policeman'];
      } else {
        // If no candidates, only allow running
        return ['run_for_policeman'];
      }
    }
    }

    // Reset form
    setSelectedAction('');
    setTargetPlayer('');
  };

  // Define available actions based on phase and role
  const getAvailableActions = () => {
    console.log('Getting available actions for phase:', gamePhase);
    console.log('Player role:', playerRole);

    switch (gamePhase) {
      case 'NIGHT':
        switch (playerRole) {
          case 'WEREWOLF':
            return ['kill','sleep'];
          case 'SEER':
            return ['check'];
          case 'WITCH':
            return ['heal', 'poison'];
          default:
            return ['sleep'];
        }

      case 'DAY':
        return ['vote'];

      case 'POLICEMAN_SELECTION':
        // Get candidates running for policeman
        const candidates = players.filter(p => p.running_for_policeman);

        if (candidates.length > 0) {
          return ['vote_policeman'];
        } else {
          return ['run_for_policeman'];
        }

      default:
        return [];
    }
  };

  // Get available targets based on action and phase
  const getAvailableTargets = () => {
    console.log('Getting available targets for action:', selectedAction);

    if (!selectedAction) return [];

    switch (gamePhase) {
      case 'NIGHT':
        // For night actions, only target alive players
        return players.filter(player =>
          player.status === 'ALIVE' &&
          player.player_id !== currentPlayer
        );

      case 'DAY':
        // For day voting, only target alive players
        return players.filter(player =>
          player.status === 'ALIVE' &&
          player.player_id !== currentPlayer
        );

      case 'POLICEMAN_SELECTION':
        if (selectedAction === 'vote_policeman') {
          // Only target players running for policeman
          return players.filter(player => player.running_for_policeman);
        }
        return [];

      default:
        return [];
    }
  };

  // Available actions for the current phase and role
  const availableActions = getAvailableActions();
  const availableTargets = getAvailableTargets();

  return (
    <div className="bg-white p-4 rounded-lg shadow">
      <h2 className="text-xl font-semibold mb-4">Actions</h2>

      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block mb-2">Action:</label>
          <select
            value={selectedAction}
            onChange={(e) => {
              console.log('Selected action:', e.target.value);
              setSelectedAction(e.target.value);
              setTargetPlayer(''); // Reset target when action changes
            }}
            className="w-full p-2 border rounded"
          >
            <option value="">Select action</option>
            {availableActions.map((action) => (
              <option key={action} value={action}>
                {action}
              </option>
            ))}
          </select>
        </div>

        {selectedAction && availableTargets.length > 0 && (
          <div>
            <label className="block mb-2">Target:</label>
            <select
              value={targetPlayer}
              onChange={(e) => {
                console.log('Selected target:', e.target.value);
                setTargetPlayer(e.target.value);
              }}
              className="w-full p-2 border rounded"
              required
            >
              <option value="">Select target</option>
              {availableTargets.map((player) => (
                <option key={player.player_id} value={player.player_id}>
                  Player {player.position}
                </option>
              ))}
            </select>
          </div>
        )}

        <button
          type="submit"
          className="bg-blue-500 text-white px-4 py-2 rounded w-full"
          disabled={!selectedAction || (availableTargets.length > 0 && !targetPlayer)}
        >
          Submit Action
        </button>
      </form>
    </div>
  );
};