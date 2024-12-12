import React, { useState, useEffect } from "react";
import axios from "axios";

interface Player {
  player_id: number;
  web_name: string;
}

interface AutocompleteProps {
  placeholder: string;
  onPlayerSelect: (player: Player) => void; // Callback to send player data to parent
}

const Autocomplete: React.FC<AutocompleteProps> = ({ placeholder, onPlayerSelect }) => {
  const [searchTerm, setSearchTerm] = useState<string>("");
  const [suggestions, setSuggestions] = useState<Player[]>([]);
  const [showSuggestions, setShowSuggestions] = useState<boolean>(false);

  useEffect(() => {
    const fetchSuggestions = async () => {
      if (searchTerm.trim() === "") {
        setSuggestions([]);
        return;
      }

      try {
        const response = await axios.get<Player[]>('http://34.55.194.187/autocomplete', {
          params: { query: searchTerm },
        });
        console.log(response.data)
        setSuggestions(response.data);
      } catch (error) {
        console.error("Error fetching suggestions:", error);
        setSuggestions([]);
      }
    };

    const debounceFetch = setTimeout(fetchSuggestions, 300); // Debounce API calls
    return () => clearTimeout(debounceFetch); // Cleanup on re-render
  }, [searchTerm]);

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setSearchTerm(e.target.value);
    setShowSuggestions(true);
  };

  const handleSuggestionClick = (player: Player) => {
    setSearchTerm(player.web_name);
    setShowSuggestions(false);
    onPlayerSelect(player); // Pass selected player to parent
  };

  return (
    <div style={{ position: "relative", width: "300px" }}>
      <input
        type="text"
        value={searchTerm}
        onChange={handleInputChange}
        placeholder={placeholder}
        style={{
          width: "100%",
          padding: "8px",
          boxSizing: "border-box",
          border: "1px solid #ccc",
          borderRadius: "4px",
        }}
      />
      {showSuggestions && suggestions.length > 0 && (
        <ul
          style={{
            position: "absolute",
            top: "40px",
            width: "100%",
            border: "1px solid #ccc",
            borderRadius: "4px",
            backgroundColor: "white",
            listStyle: "none",
            padding: 0,
            margin: 0,
            maxHeight: "150px",
            overflowY: "auto",
            zIndex: 1000,
          }}
        >
          {suggestions.map((player) => (
            <li
              key={player.player_id}
              onClick={() => handleSuggestionClick(player)}
              style={{
                padding: "8px",
                cursor: "pointer",
                backgroundColor: "white", // Ensure it's not transparent
                color: "black", // Make text visible  
              }}
              onMouseDown={(e) => e.preventDefault()} // Prevent input blur
            >
              {player.web_name}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
};

export default Autocomplete;
