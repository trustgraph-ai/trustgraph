/**
 * textToBase64 using TextEncoder
 */
export const textToBase64 = (input) => {
  // Convert string to UTF-8 bytes, then to Base64
  const encoder = new TextEncoder();
  const bytes = encoder.encode(input);

  // Convert Uint8Array to string for btoa()
  const binaryString = Array.from(bytes, (byte) =>
    String.fromCharCode(byte),
  ).join("");
  return btoa(binaryString);
};

/**
 * Converts a text string to Base64 encoding with proper UTF-8 handling
 *
 * WHY THIS LOOKS WEIRD:
 * FileReader.readAsDataURL() returns a data URL like
 * "data:image/png;base64,iVBORw0KGgoA..."
 * but we only want the Base64 part. The regex removes the "data:" prefix
 * and everything up to the comma, leaving just the Base64 data.
 *
 * ISSUES WITH CURRENT IMPLEMENTATION:
 * - Type assertion (as string) is unsafe - reader.result could be ArrayBuffer
 * - No error handling for failed file reads
 * - Regex is overly complex for simple string removal
 *
 * @param {File} file - The file to convert to Base64
 * @returns {Promise<string>} Promise that resolves to Base64 string
 */
export const fileToBase64 = (file) => {
  return new Promise((resolve) => {
    const reader = new FileReader();

    reader.onloadend = () => {
      // FIXME: Type is 'string | ArrayBuffer'?  is this safe?
      // FIXME: Use Blob.arrayBuffer API?
      const data = (reader.result as string)
        .replace("data:", "")
        .replace(/^.+,/, "");

      resolve(data);
    };

    reader.readAsDataURL(file);
  });
};
