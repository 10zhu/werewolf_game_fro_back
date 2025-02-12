// src/components/RoomList.js
import React, { useState, useEffect } from 'react';

export const RoomList = ({ onSelectRoom }) => {
  const [rooms, setRooms] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchRooms = async () => {
      try {
        const response = await fetch('http://localhost:8000/api/games/available_rooms/');
        const data = await response.json();
        setRooms(data.rooms);
        setLoading(false);
      } catch (err) {
        setError('Failed to fetch available rooms');
        setLoading(false);
      }
    };

    fetchRooms();
    // Poll for room updates every 5 seconds
    const interval = setInterval(fetchRooms, 5000);
    return () => clearInterval(interval);
  }, []);

  if (loading) {
    return (
      <div className="bg-white p-6 rounded-lg shadow-md">
        <p className="text-gray-600">Loading available rooms...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-white p-6 rounded-lg shadow-md">
        <p className="text-red-500">{error}</p>
      </div>
    );
  }

  return (
    <div className="bg-white p-6 rounded-lg shadow-md">
      <h2 className="text-2xl font-bold mb-6">Available Rooms</h2>

      {rooms.length === 0 ? (
        <p className="text-gray-600">No active rooms available. Create a new game to start!</p>
      ) : (
        <div className="space-y-4">
          {rooms.map((room) => (
            <div
              key={room.session_id}
              className="border rounded-lg p-4 hover:bg-gray-50 transition-colors cursor-pointer"
              onClick={() => onSelectRoom(room.session_id)}
            >
              <div className="flex justify-between items-start mb-2">
                <h3 className="text-lg font-semibold">Room {room.session_id.slice(0, 8)}...</h3>
                <span className={`px-3 py-1 rounded-full text-sm ${
                  room.waiting_for_actions
                    ? 'bg-yellow-100 text-yellow-800'
                    : 'bg-green-100 text-green-800'
                }`}>
                  {room.waiting_for_actions ? 'Waiting for actions' : 'Ready for next phase'}
                </span>
              </div>

              <div className="grid grid-cols-2 gap-4 text-sm text-gray-600">
                <div>
                  <p>Phase: {room.phase}</p>
                  <p>Round: {room.round}</p>
                </div>
                <div>
                  <p>Players: {room.alive_players}/{room.total_players}</p>
                  <p>Pending Actions: {room.pending_actions_count}</p>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};