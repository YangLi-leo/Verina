"use client";

interface CitationBubbleProps {
  url: string;
  title: string;
  number: number;
}

export default function CitationBubble({ url, title, number }: CitationBubbleProps) {
  // Extract domain from URL
  const getDomain = (url: string) => {
    try {
      const hostname = new URL(url).hostname;
      // Remove www. and get short version
      const domain = hostname.replace("www.", "");
      // Get first part for common domains
      if (domain.includes(".")) {
        const parts = domain.split(".");
        // Return recognizable short names for common sites
        const shortNames: Record<string, string> = {
          wikipedia: "Wiki",
          reddit: "Reddit",
          github: "GitHub",
          stackoverflow: "Stack",
          youtube: "YouTube",
          google: "Google",
          medium: "Medium",
        };
        const siteName = parts[0].toLowerCase();
        return shortNames[siteName] || parts[0];
      }
      return domain;
    } catch {
      return `Source ${number}`;
    }
  };

  const displayText = getDomain(url);

  return (
    <span
      onClick={() => window.open(url, "_blank")}
      title={title}
      className="mx-0.5 inline-flex transform cursor-pointer select-none
                 items-center rounded-full
                 border border-gray-200/20 bg-gray-100/60 px-1.5
                 py-[2px] align-baseline text-[10px]
                 font-normal text-gray-500
                 transition-all
                 duration-150 ease-out hover:scale-[1.02]
                 hover:border-blue-200/30 hover:bg-blue-100/60
                 hover:text-blue-600 hover:shadow-sm"
    >
      <span className="opacity-95">{displayText}</span>
    </span>
  );
}
