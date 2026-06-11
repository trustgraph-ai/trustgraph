/**
 * Generate a test PDF for pipeline testing.
 *
 * Creates a 2-page PDF with clear entity relationships that the
 * extractor can identify. Writes to data/test.pdf.
 */

import { PDFDocument, StandardFonts } from "pdf-lib";
import { writeFileSync, mkdirSync } from "node:fs";

const PAGE_1 = `Acme Corporation: Company Overview

Alice Johnson is a senior engineer at Acme Corporation. She has been with the company since 2020 and leads the backend engineering team.

Acme Corporation develops CloudSync, a cloud storage platform designed for enterprise customers. CloudSync uses Amazon Web Services (AWS) infrastructure for hosting and runs on Kubernetes for container orchestration.

CloudSync provides automatic file synchronization, end-to-end encryption, and team collaboration features. The platform serves over 500 enterprise clients worldwide.`;

const PAGE_2 = `Acme Corporation: Leadership and Competition

Bob Chen is the Chief Technology Officer (CTO) of Acme Corporation. Alice Johnson reports directly to Bob. Together they oversee the technical direction of CloudSync.

CloudSync was officially launched in January 2024. The platform competes with established players including Dropbox, Google Drive, and Microsoft OneDrive.

Acme Corporation is headquartered in San Francisco, California. The company employs approximately 200 people across engineering, sales, and operations departments.`;

async function main(): Promise<void> {
  const pdf = await PDFDocument.create();
  const font = await pdf.embedFont(StandardFonts.Helvetica);
  const boldFont = await pdf.embedFont(StandardFonts.HelveticaBold);

  for (const [i, text] of [PAGE_1, PAGE_2].entries()) {
    const page = pdf.addPage([612, 792]); // US Letter
    const lines = text.split("\n");
    let y = 750;

    for (const line of lines) {
      if (!line.trim()) {
        y -= 14;
        continue;
      }

      const isTitle = i === 0 ? line.startsWith("Acme") : line.startsWith("Acme");
      const useFont = line === lines[0] ? boldFont : font;
      const size = line === lines[0] ? 16 : 11;

      page.drawText(line.trim(), {
        x: 50,
        y,
        size,
        font: useFont,
      });
      y -= size + 6;
    }
  }

  const pdfBytes = await pdf.save();

  mkdirSync("data", { recursive: true });
  writeFileSync("data/test.pdf", pdfBytes);
  console.log(`Created data/test.pdf (${pdfBytes.length} bytes, 2 pages)`);
}

main().catch((err) => {
  console.error("Failed to create test PDF:", err);
  process.exit(1);
});
