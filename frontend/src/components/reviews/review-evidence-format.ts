export function formatEvidenceMimeType(mimeType: string) {
  const known: Record<string, string> = {
    "application/pdf": "PDF",
    "application/msword": "DOC",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
      "DOCX",
    "application/vnd.ms-excel": "XLS",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "XLSX",
    "image/jpeg": "JPG",
    "image/png": "PNG",
  };
  return (
    known[mimeType] ?? mimeType.split("/").at(-1)?.toUpperCase() ?? mimeType
  );
}
