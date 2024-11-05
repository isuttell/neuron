import ImageForm from "../images/ImageForm";
import { useAppSelector } from "../hooks";

import { getImages } from "../slices/imagesSlice";
import Loading from "../lib/loading";

export default function Image() {
  const images = useAppSelector(getImages);

  const latestImages = [...images].sort((a, b) =>
    a.created_at > b.created_at ? -1 : 1
  );

  const image = latestImages[0];

  return (
    <div className="flex flex-1 p-4 flex-col flex-nowrap max-h-screen overflow-hidden">
      <div className="flex justify-between mb-2 border-b pb-2">
        <h1 className="text-2xl font-bold">Image Generator</h1>
      </div>

      <div className="flex-1 flex flex-col h-full ">
        {image?.image ? (
          <>
            <div
              style={{ backgroundImage: `url(${image.image})` }}
              className="w-full h-full bg-contain bg-no-repeat bg-center rounded-lg"
              aria-label={image.prompt}
            />
            <div className="text-center text-sm text-gray-500 my-2">
              {image.prompt.slice(0, 256)}
            </div>
          </>
        ) : (
          <Loading />
        )}
      </div>
      <div className="bottom-0">
        <ImageForm className="bg-background" />
      </div>
    </div>
  );
}
