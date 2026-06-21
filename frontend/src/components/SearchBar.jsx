import { useState } from "react";

export default function SearchBar({ onSearch, defaultValue }) {
  const [value, setValue] = useState(defaultValue || "");

  function handleSubmit(e) {
    e.preventDefault();
    if (value.trim()) onSearch(value.trim());
  }

  return (
    <form className="search-bar" onSubmit={handleSubmit}>
      <span className="search-bar__icon mono">acct_id</span>
      <input
        type="text"
        className="mono"
        placeholder="e.g. 22513864"
        value={value}
        onChange={(e) => setValue(e.target.value)}
      />
      <button type="submit" className="mono">trace</button>
    </form>
  );
}