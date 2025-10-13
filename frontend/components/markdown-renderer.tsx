"use client";
import { logger } from "@/lib/logger";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { Components } from "react-markdown";
import CitationBubble from "./citation-bubble";
import { Fragment } from "react";

interface MarkdownRendererProps {
  content: string;
  sources?: Array<{
    idx: number;
    title: string;
    url: string;
  }>;
}

export default function MarkdownRenderer({ content, sources = [] }: MarkdownRendererProps) {
  // Debug: Log sources array
  logger.log(
    "[MarkdownRenderer] Sources:",
    sources.map(s => ({ idx: s.idx, title: s.title.substring(0, 50) }))
  );

  // Split content by citation patterns and create components
  // Supports both [1] and [1, 2, 3] formats
  const renderContentWithCitations = (text: string) => {
    const parts = text.split(/(\[\d+(?:,\s*\d+)*\])/g);

    return parts.map((part, index) => {
      const citationMatch = part.match(/\[(\d+(?:,\s*\d+)*)\]/);
      if (citationMatch) {
        // Extract all numbers from the citation
        const numbers = citationMatch[1].split(/,\s*/).map(n => parseInt(n.trim()));

        // Create a bubble for each number
        return (
          <Fragment key={index}>
            {numbers.map((num, i) => {
              const source = sources.find(s => s.idx === num);
              logger.log(`[Citation] Looking for idx=${num}, found:`, source ? "YES" : "NO");
              if (source) {
                return (
                  <CitationBubble
                    key={`${index}-${i}`}
                    number={num}
                    url={source.url}
                    title={source.title}
                  />
                );
              }
              return null;
            })}
          </Fragment>
        );
      }
      return <Fragment key={index}>{part}</Fragment>;
    });
  };

  // Custom components for markdown elements
  const components: Components = {
    // Customize paragraph rendering to handle citations
    p: ({ children }) => {
      // Process children to replace citation patterns
      const processChildren = (children: any): any => {
        if (typeof children === "string") {
          return renderContentWithCitations(children);
        }
        if (Array.isArray(children)) {
          return children.map((child, i) => {
            if (typeof child === "string") {
              return <Fragment key={i}>{renderContentWithCitations(child)}</Fragment>;
            }
            return child;
          });
        }
        return children;
      };

      return (
        <p className="overflow-wrap-anywhere mb-4 break-words leading-relaxed text-black">
          {processChildren(children)}
        </p>
      );
    },

    // Regular links
    a: ({ href, children }) => (
      <a
        href={href}
        target="_blank"
        rel="noopener noreferrer"
        className="break-words text-blue-600 underline hover:text-blue-800"
      >
        {children}
      </a>
    ),

    // Customize list rendering
    ul: ({ children }) => <ul className="mb-4 ml-6 list-disc space-y-1">{children}</ul>,

    ol: ({ children }) => <ol className="mb-4 ml-6 list-decimal space-y-1">{children}</ol>,

    li: ({ children }) => {
      const processChildren = (children: any): any => {
        if (typeof children === "string") {
          return renderContentWithCitations(children);
        }
        if (Array.isArray(children)) {
          return children.map((child, i) => {
            if (typeof child === "string") {
              return <Fragment key={i}>{renderContentWithCitations(child)}</Fragment>;
            }
            return child;
          });
        }
        return children;
      };

      return <li className="break-words text-black">{processChildren(children)}</li>;
    },

    // Customize heading rendering
    h1: ({ children }) => {
      const processChildren = (children: any): any => {
        if (typeof children === "string") {
          return renderContentWithCitations(children);
        }
        if (Array.isArray(children)) {
          return children.map((child, i) => {
            if (typeof child === "string") {
              return <Fragment key={i}>{renderContentWithCitations(child)}</Fragment>;
            }
            return child;
          });
        }
        return children;
      };

      return (
        <h1 className="mb-4 break-words text-2xl font-bold text-gray-900">
          {processChildren(children)}
        </h1>
      );
    },

    h2: ({ children }) => {
      const processChildren = (children: any): any => {
        if (typeof children === "string") {
          return renderContentWithCitations(children);
        }
        if (Array.isArray(children)) {
          return children.map((child, i) => {
            if (typeof child === "string") {
              return <Fragment key={i}>{renderContentWithCitations(child)}</Fragment>;
            }
            return child;
          });
        }
        return children;
      };

      return (
        <h2 className="mb-3 break-words text-xl font-semibold text-gray-900">
          {processChildren(children)}
        </h2>
      );
    },

    h3: ({ children }) => {
      const processChildren = (children: any): any => {
        if (typeof children === "string") {
          return renderContentWithCitations(children);
        }
        if (Array.isArray(children)) {
          return children.map((child, i) => {
            if (typeof child === "string") {
              return <Fragment key={i}>{renderContentWithCitations(child)}</Fragment>;
            }
            return child;
          });
        }
        return children;
      };

      return (
        <h3 className="mb-2 break-words text-lg font-semibold text-gray-900">
          {processChildren(children)}
        </h3>
      );
    },

    // Customize code blocks
    code: ({ className, children }) => {
      const isInline = !className;

      if (isInline) {
        return (
          <code className="rounded bg-gray-100 px-1.5 py-0.5 font-mono text-sm text-gray-800">
            {children}
          </code>
        );
      }

      return (
        <code className="block overflow-x-auto rounded-lg bg-gray-50 p-4 font-mono text-sm text-gray-800">
          {children}
        </code>
      );
    },

    // Customize blockquote
    blockquote: ({ children }) => {
      const processChildren = (children: any): any => {
        if (typeof children === "string") {
          return renderContentWithCitations(children);
        }
        if (Array.isArray(children)) {
          return children.map((child, i) => {
            if (typeof child === "string") {
              return <Fragment key={i}>{renderContentWithCitations(child)}</Fragment>;
            }
            return child;
          });
        }
        return children;
      };

      return (
        <blockquote className="my-4 border-l-4 border-gray-300 pl-4 italic text-gray-600">
          {processChildren(children)}
        </blockquote>
      );
    },

    // Customize strong/bold text
    strong: ({ children }) => {
      const processChildren = (children: any): any => {
        if (typeof children === "string") {
          return renderContentWithCitations(children);
        }
        if (Array.isArray(children)) {
          return children.map((child, i) => {
            if (typeof child === "string") {
              return <Fragment key={i}>{renderContentWithCitations(child)}</Fragment>;
            }
            return child;
          });
        }
        return children;
      };

      return <strong className="font-semibold text-gray-900">{processChildren(children)}</strong>;
    },

    // Customize emphasis/italic text
    em: ({ children }) => {
      const processChildren = (children: any): any => {
        if (typeof children === "string") {
          return renderContentWithCitations(children);
        }
        if (Array.isArray(children)) {
          return children.map((child, i) => {
            if (typeof child === "string") {
              return <Fragment key={i}>{renderContentWithCitations(child)}</Fragment>;
            }
            return child;
          });
        }
        return children;
      };

      return <em className="italic">{processChildren(children)}</em>;
    },

    // Customize horizontal rule
    hr: () => <hr className="my-6 border-gray-200" />,

    // Customize table rendering
    table: ({ children }) => (
      <div className="mb-4 overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200">{children}</table>
      </div>
    ),

    thead: ({ children }) => <thead className="bg-gray-50">{children}</thead>,

    tbody: ({ children }) => (
      <tbody className="divide-y divide-gray-200 bg-white">{children}</tbody>
    ),

    th: ({ children }) => {
      const processChildren = (children: any): any => {
        if (typeof children === "string") {
          return renderContentWithCitations(children);
        }
        if (Array.isArray(children)) {
          return children.map((child, i) => {
            if (typeof child === "string") {
              return <Fragment key={i}>{renderContentWithCitations(child)}</Fragment>;
            }
            return child;
          });
        }
        return children;
      };

      return (
        <th className="px-4 py-2 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
          {processChildren(children)}
        </th>
      );
    },

    td: ({ children }) => {
      const processChildren = (children: any): any => {
        if (typeof children === "string") {
          return renderContentWithCitations(children);
        }
        if (Array.isArray(children)) {
          return children.map((child, i) => {
            if (typeof child === "string") {
              return <Fragment key={i}>{renderContentWithCitations(child)}</Fragment>;
            }
            return child;
          });
        }
        return children;
      };

      return <td className="px-4 py-2 text-sm text-black">{processChildren(children)}</td>;
    },
  };

  return (
    <div className="w-full max-w-none break-words">
      <ReactMarkdown remarkPlugins={[remarkGfm]} components={components}>
        {content}
      </ReactMarkdown>
    </div>
  );
}
