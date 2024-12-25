import React, { useEffect, useState } from "react";
import { useLocation } from "react-router-dom";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { oneDark } from "react-syntax-highlighter/dist/esm/styles/prism";
import { Spinner } from "@/components/ui/spinner";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeRaw from "rehype-raw";
import remarkMath from "remark-math";
import rehypeKatex from "rehype-katex";
import "katex/dist/katex.min.css";
import "@/index.css";

const getLanguage = (fileUrl: string) => {
  if (/.py$/.test(fileUrl)) {
    return "python";
  } else if (/.js$/.test(fileUrl)) {
    return "javascript";
  } else if (/.md$/.test(fileUrl)) {
    return "markdown";
  }
  return "text";
};

const CodeViewer: React.FC = () => {
  const location = useLocation();

  const queryParams = new URLSearchParams(location.search);
  const fileUrl = queryParams.get("url");
  const [code, setCode] = useState<string>("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(false);

  useEffect(() => {
    const fetchCode = async () => {
      if (!fileUrl) {
        return;
      }

      try {
        setLoading(true);
        const response = await fetch(decodeURIComponent(fileUrl));
        if (!response.ok) {
          throw new Error("Network response was not ok");
        }
        const text = await response.text();
        setCode(text);
      } catch (error) {
        console.error("Error fetching the code:", error);
        setError("Error fetching the file");
      } finally {
        setLoading(false);
      }
    };

    fetchCode();
  }, [fileUrl]);

  if (!fileUrl) {
    return (
      <div className="p-4 flex justify-center items-center h-full">
        <div className="flex flex-col items-center gap-2">
          No file URL provided
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-4 flex justify-center items-center h-full">
        <div className="flex flex-col items-center gap-2">Error: {error}</div>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="p-4 flex justify-center items-center h-full">
        <div className="flex flex-col items-center gap-2">
          <Spinner />
        </div>
      </div>
    );
  }
  const language = getLanguage(fileUrl);

  if (language === "markdown" || language === "text") {
    return (
      <div className="mx-2">
        <ReactMarkdown
          className="whitespace-pre-line"
          children={code}
          remarkPlugins={[remarkGfm, remarkMath]}
          rehypePlugins={[rehypeRaw, rehypeKatex]}
        />
      </div>
    );
  }

  return (
    <div className="mx-2">
      <SyntaxHighlighter
        className=""
        language={getLanguage(fileUrl)}
        style={oneDark}
      >
        {code}
      </SyntaxHighlighter>
    </div>
  );
};

export default CodeViewer;
