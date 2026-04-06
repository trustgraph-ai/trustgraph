export const timeString = (time) => {
  const tm = new Date(time * 1000);
  return tm.toLocaleDateString() + " " + tm.toLocaleTimeString();
};
