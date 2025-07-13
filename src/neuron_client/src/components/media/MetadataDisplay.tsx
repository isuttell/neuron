interface MetadataDisplayProps {
  metadata: Record<string, unknown>;
  description?: string;
  dimensions?: { width?: number; height?: number };
  className?: string;
}

export const MetadataDisplay: React.FC<MetadataDisplayProps> = ({
  metadata,
  description,
  dimensions,
  className,
}) => {
  const hasMetadata = metadata && Object.keys(metadata).length > 0;
  const hasDimensions = dimensions?.width || dimensions?.height;

  if (!description && !hasDimensions && !hasMetadata) {
    return null;
  }

  return (
    <div className={className}>
      {description && (
        <div>
          <h3 className="text-sm font-medium text-muted-foreground mb-2">Description</h3>
          <p className="text-sm whitespace-pre-wrap">{description}</p>
        </div>
      )}

      {hasDimensions && (
        <div>
          <h3 className="text-sm font-medium text-muted-foreground mb-2">Dimensions</h3>
          <p className="text-sm">
            {dimensions.width && dimensions.height
              ? `${dimensions.width} × ${dimensions.height}`
              : dimensions.width
                ? `Width: ${dimensions.width}`
                : `Height: ${dimensions.height}`
            }
          </p>
        </div>
      )}

      {hasMetadata && (
        <>
          <div className="border-t -mx-6 my-4" />
          <dl>
            {Object.entries(metadata)
              .filter(([, value]) => value !== null && value !== undefined && value !== '')
              .map(([key, value]) => (
                <div key={key} className="text-sm mb-4">
                  <dt className="font-medium text-muted-foreground capitalize mb-1">
                    {key.replace(/_/g, ' ')}
                  </dt>
                  <dd className="text-foreground break-words">{String(value)}</dd>
                </div>
              ))
            }
          </dl>
        </>
      )}
    </div>
  );
};
