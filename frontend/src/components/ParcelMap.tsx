"use client";

import React, { useEffect } from "react";
import { MapContainer, TileLayer, Marker, Popup, useMap } from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { CivicFeedItem, ParcelLocation } from "@/types/civic";

// Fix Leaflet's default marker icons in Next.js
const defaultIcon = L.icon({
  iconUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png",
  iconRetinaUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png",
  shadowUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
  shadowSize: [41, 41],
});

interface ParcelMapProps {
  items: CivicFeedItem[];
  selectedItem?: CivicFeedItem | null;
  onSelectPin?: (item: CivicFeedItem) => void;
}

// Controller to auto-pan when a pin or item is selected
function MapController({ center }: { center: [number, number] }) {
  const map = useMap();
  useEffect(() => {
    map.setView(center, map.getZoom() < 13 ? 14 : map.getZoom());
  }, [center, map]);
  return null;
}

export default function ParcelMap({
  items,
  selectedItem,
  onSelectPin,
}: ParcelMapProps) {
  // Collect all items with valid coordinates (or mock coordinates for local display)
  const markers: { item: CivicFeedItem; loc: ParcelLocation; coords: [number, number] }[] = [];

  // Default coordinate center (e.g. Virginia Beach / Richmond area or fallback)
  const defaultCenter: [number, number] = [36.8529, -75.9780];

  items.forEach((item, itemIdx) => {
    item.locations.forEach((loc, locIdx) => {
      // If latitude/longitude is present, use it; otherwise provide a synthetic deterministic offset for local demo
      const lat = loc.latitude ?? (defaultCenter[0] + (itemIdx * 0.008) - (locIdx * 0.003));
      const lng = loc.longitude ?? (defaultCenter[1] + (itemIdx * 0.007) + (locIdx * 0.004));
      markers.push({
        item,
        loc,
        coords: [lat, lng],
      });
    });
  });

  const activeCoords = markers.find((m) => m.item.id === selectedItem?.id)?.coords || defaultCenter;

  return (
    <div className="parcel-map-container h-[260px] w-full rounded-xl overflow-hidden border border-border shadow-sm relative z-0">
      <MapContainer
        center={defaultCenter}
        zoom={13}
        scrollWheelZoom={true}
        className="h-full w-full"
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        <MapController center={activeCoords} />
        {markers.map((m, idx) => {
          return (
            <Marker
              key={idx}
              position={m.coords}
              icon={defaultIcon}
              eventHandlers={{
                click: () => {
                  if (onSelectPin) onSelectPin(m.item);
                },
              }}
            >
              <Popup>
                <div className="p-1 space-y-1 text-xs">
                  <div className="font-bold text-primary">{m.loc.address || m.loc.parcel_id || m.loc.raw_match}</div>
                  <div className="text-[11px] font-medium text-foreground">{m.item.title}</div>
                  <div className="text-[10px] text-muted-foreground">Ordinance: {m.item.ordinance_id || "N/A"} • Page {m.item.page_start}</div>
                </div>
              </Popup>
            </Marker>
          );
        })}
      </MapContainer>
    </div>
  );
}
