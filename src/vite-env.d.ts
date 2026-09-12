/// <reference types="vite/client" />

declare module 'virtual:room-catalog' {
  const catalog: {
    rooms: Array<{
      id: string;
      name: string;
      image: string;
      width: number;
      height: number;
      seatCount: number;
    }>;
  };
  export default catalog;
}
