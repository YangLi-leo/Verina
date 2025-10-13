"use client";

import { FileText, ExternalLink } from "lucide-react";
import type { Artifact } from "@/types";

interface ArtifactCardProps {
  artifact: Artifact;
}

/**
 * ArtifactCard - Display artifact preview card with title
 * Shows a clickable card that opens the full HTML content in a new tab
 */
export default function ArtifactCard({ artifact }: ArtifactCardProps) {
  const formatSize = (kb: number): string => {
    if (kb < 1) return `${(kb * 1024).toFixed(0)}B`;
    if (kb < 1024) return `${kb.toFixed(1)}KB`;
    return `${(kb / 1024).toFixed(1)}MB`;
  };

  const getArtifactIcon = (type: string) => {
    switch (type) {
      case "html_blog":
        return <FileText className="h-5 w-5" />;
      default:
        return <FileText className="h-5 w-5" />;
    }
  };

  const getArtifactLabel = (type: string) => {
    switch (type) {
      case "html_blog":
        return "Interactive Report";
      default:
        return "Artifact";
    }
  };

  // Extract metadata fields with defaults
  const fileSize = artifact.metadata?.file_size_kb || 0;

  // Open artifact in a new tab like Notion blog export
  const handleOpenArtifact = () => {
    if (!artifact.html_content) return;

    // Create a standalone HTML page with the artifact content
    const fullHTML = `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>${artifact.title}</title>
  <style>
    * {
      margin: 0;
      padding: 0;
      box-sizing: border-box;
    }

    body {
      font-family: -apple-system, BlinkMacSystemFont, 'Inter', 'SF Pro Display', 'Segoe UI', Roboto, sans-serif;
      background: #fafafa;
      padding: 48px 64px;
      line-height: 1.6;
      color: #374151;
    }

    @media (min-width: 1024px) {
      body {
        padding: 56px 80px;
      }
    }

    @media (min-width: 1440px) {
      body {
        padding: 64px 96px;
      }
    }

    h1 {
      font-size: 2rem;
      font-weight: 700;
      margin: 2.5rem 0 1.5rem;
      line-height: 1.25;
      color: #111827;
      letter-spacing: -0.02em;
    }

    @media (min-width: 1024px) {
      h1 {
        font-size: 2.5rem;
        margin: 3rem 0 1.75rem;
      }
    }

    h1:first-child {
      margin-top: 0;
    }

    h2 {
      font-size: 1.5rem;
      font-weight: 650;
      margin: 2.5rem 0 1.25rem;
      color: #1f2937;
      line-height: 1.35;
      letter-spacing: -0.015em;
      padding-bottom: 0.75rem;
      border-bottom: 1.5px solid #e5e7eb;
    }

    @media (min-width: 1024px) {
      h2 {
        font-size: 1.75rem;
        margin: 3rem 0 1.5rem;
      }
    }

    h3 {
      font-size: 1.25rem;
      font-weight: 600;
      margin: 2rem 0 1rem;
      color: #374151;
      line-height: 1.4;
      letter-spacing: -0.01em;
    }

    @media (min-width: 1024px) {
      h3 {
        font-size: 1.375rem;
        margin: 2.25rem 0 1.125rem;
      }
    }

    p {
      margin-bottom: 1.5rem;
      line-height: 1.75;
      color: #4b5563;
      font-size: 1rem;
    }

    @media (min-width: 1024px) {
      p {
        line-height: 1.8;
        font-size: 1.0625rem;
      }
    }

    ul, ol {
      margin: 1.5rem 0;
      padding-left: 2rem;
    }

    li {
      margin-bottom: 0.75rem;
      color: #4b5563;
      line-height: 1.75;
    }

    @media (min-width: 1024px) {
      li {
        line-height: 1.8;
      }
    }

    a {
      color: #2563eb;
      text-decoration: none;
      border-bottom: 1px solid transparent;
      transition: all 0.2s ease;
    }

    a:hover {
      color: #1d4ed8;
      border-bottom-color: #1d4ed8;
    }

    pre {
      background: #f8f9fa;
      border: 1px solid #e5e7eb;
      border-radius: 12px;
      padding: 20px;
      margin: 2rem 0;
      overflow-x: auto;
      font-family: 'SF Mono', Monaco, 'Cascadia Code', 'Roboto Mono', Consolas, monospace;
      font-size: 0.9rem;
      line-height: 1.6;
    }

    code {
      background: #f1f3f5;
      padding: 0.2rem 0.4rem;
      border-radius: 6px;
      font-size: 0.9em;
      font-family: 'SF Mono', Monaco, 'Cascadia Code', 'Roboto Mono', Consolas, monospace;
      color: #e74c3c;
    }

    blockquote {
      border-left: 3px solid #d1d5db;
      margin: 2rem 0;
      padding: 1rem 1.75rem;
      background: #f9fafb;
      font-style: normal;
      color: #6b7280;
      border-radius: 0 8px 8px 0;
    }

    table {
      width: 100%;
      border-collapse: separate;
      border-spacing: 0;
      margin: 2.5rem 0;
      border-radius: 12px;
      border: 1px solid #e5e7eb;
      background: white;
      overflow: hidden;
    }

    thead {
      background: linear-gradient(to bottom, #f9fafb 0%, #f3f4f6 100%);
    }

    th {
      padding: 0.875rem 1rem;
      text-align: left;
      font-weight: 600;
      border-bottom: 2px solid #e5e7eb;
      font-size: 0.875rem;
      color: #374151;
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }

    td {
      padding: 0.875rem 1rem;
      border-bottom: 1px solid #f3f4f6;
      font-size: 0.9375rem;
      word-break: break-word;
      color: #4b5563;
      line-height: 1.6;
      transition: background-color 0.15s ease;
    }

    tbody tr:hover td {
      background-color: #f9fafb;
    }

    tbody tr:last-child td {
      border-bottom: none;
    }

    hr {
      border: none;
      height: 1px;
      background: linear-gradient(to right, transparent, #e5e7eb, transparent);
      margin: 3rem 0;
    }

    strong {
      font-weight: 600;
      color: #1f2937;
    }

    em {
      font-style: italic;
      color: #4b5563;
    }
  </style>
</head>
<body>
  ${artifact.html_content}
</body>
</html>`;

    // Create a Blob URL for the HTML content (enables clickable links)
    const blob = new Blob([fullHTML], { type: "text/html" });
    const blobUrl = URL.createObjectURL(blob);

    // Open in new tab
    const newWindow = window.open(blobUrl, "_blank");

    // Clean up the Blob URL after a short delay (window has loaded)
    if (newWindow) {
      setTimeout(() => {
        URL.revokeObjectURL(blobUrl);
      }, 1000);
    }
  };

  return (
    <div className="mt-4 rounded-lg border border-gray-200 bg-white p-4 transition-shadow hover:shadow-md">
      <div className="flex items-start gap-3">
        {/* Icon */}
        <div className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-lg bg-gray-100 text-gray-600">
          {getArtifactIcon(artifact.type)}
        </div>

        {/* Content */}
        <div className="min-w-0 flex-1">
          <div className="mb-1 flex items-center gap-2">
            <span className="text-xs font-medium uppercase tracking-wide text-gray-500">
              {getArtifactLabel(artifact.type)}
            </span>
            {fileSize > 0 && (
              <span className="text-xs text-gray-400">· {formatSize(fileSize)}</span>
            )}
          </div>

          <h4 className="mb-2 line-clamp-2 text-sm font-semibold text-gray-900">
            {artifact.title}
          </h4>

          {/* Action Button */}
          <button
            onClick={handleOpenArtifact}
            className="inline-flex items-center gap-2 rounded-md bg-blue-600 px-3 py-1.5 text-xs font-medium text-white transition-colors hover:bg-blue-700"
          >
            <ExternalLink className="h-3.5 w-3.5" />
            <span>Open Report</span>
          </button>
        </div>
      </div>
    </div>
  );
}
