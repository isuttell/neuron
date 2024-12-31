import { createSlice } from "@reduxjs/toolkit";
import type { PayloadAction } from "@reduxjs/toolkit";
import type { RootState } from "../store";
import * as actions from "../actions/imageActions";

export interface MediaFile {
  id: string;
  path: string;
  url: string;
  prompt: string | null;
  created_at: string;
  size: number;
  mime_type: string;
  media_type: string;
}

interface UpdateImagePayload {
  image: MediaFile;
}

interface DeleteImagePayload {
  image_id: string;
}

// Define a type for the slice state
interface ImageState {
  images: MediaFile[];
}

// Define the initial state using that type
const initialState: ImageState = {
  images: [],
};

function upsert(state: ImageState, image: MediaFile) {
  const existingImageIndex = state.images.findIndex(
    (img) => img.id === image.id
  );
  if (existingImageIndex !== -1) {
    state.images[existingImageIndex] = image;
  } else {
    state.images.push(image);
  }
}

export const imagesSlice = createSlice({
  name: "images",
  initialState,
  reducers: {
    upsertImage: (state, action: PayloadAction<UpdateImagePayload>) => {
      upsert(state, action.payload.image);
    },
    deleteImage: (state, action: PayloadAction<DeleteImagePayload>) => {
      state.images = state.images.filter(
        (img) => img.id !== action.payload.image_id
      );
    },
  },
  extraReducers: (builder) => {
    builder.addCase(actions.fetchImages.fulfilled, (state, action) => {
      for (const image of action.payload) {
        upsert(state, image);
      }
    });
  },
});

export const { upsertImage, deleteImage } = imagesSlice.actions;

export const getImages = (state: RootState) => state.images.images;

export default imagesSlice.reducer;
