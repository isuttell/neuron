import { createSlice } from "@reduxjs/toolkit";
import type { PayloadAction } from "@reduxjs/toolkit";
import type { RootState } from "../store";

export interface ImageModel {
  id: string;
  prompt: string;
  image: string;
  created_at: string;
  updated_at: string;
}

interface UpdateImagePayload {
  image: ImageModel;
}

interface DeleteImagePayload {
  image_id: string;
}

// Define a type for the slice state
interface ImageState {
  images: ImageModel[];
}

// Define the initial state using that type
const initialState: ImageState = {
  images: [],
};

export const imagesSlice = createSlice({
  name: "images",
  initialState,
  reducers: {
    upsertImage: (state, action: PayloadAction<UpdateImagePayload>) => {
      const existingImageIndex = state.images.findIndex(
        (img) => img.id === action.payload.image.id
      );
      if (existingImageIndex !== -1) {
        state.images[existingImageIndex] = action.payload.image;
      } else {
        state.images.push(action.payload.image);
      }
    },
    deleteImage: (state, action: PayloadAction<DeleteImagePayload>) => {
      state.images = state.images.filter(
        (img) => img.id !== action.payload.image_id
      );
    },
  },
});

export const { upsertImage, deleteImage } = imagesSlice.actions;

export const getImages = (state: RootState) => state.images.images;

export default imagesSlice.reducer;
