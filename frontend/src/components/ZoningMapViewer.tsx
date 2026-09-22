"use client";

import React, { useEffect } from "react";
import { MapContainer, TileLayer, Marker, Popup, Polygon, Polyline, useMap } from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";

const defaultIcon = L.icon({
  iconUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png",
  iconRetinaUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png",
  shadowUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
  shadowSize: [41, 41],
});

export interface ZoningZone {
  id: string;
  name: string;
  code: string;
  type: "residential" | "commercial" | "industrial" | "mixed-use";
  color: string;
  polygon: [number, number][]; // Array of lat/lng points forming the boundary lines
  description?: string;
}

export interface ParcelMarker {
  id: string;
  address: string;
  parcelId?: string;
  coords: [number, number];
  ordinanceId?: string;
  page?: number;
  details?: string;
}

interface ZoningMapViewerProps {
  zones?: ZoningZone[];
  markers?: ParcelMarker[];
  activeMarkerId?: string | null;
  onSelectMarker?: (marker: ParcelMarker) => void;
}

// Sample zoning boundary lines for demo visualization
const SAMPLE_ZONES: ZoningZone[] = [
  {
    id: "zone-r1",
    name: "R-1 Low Density Single Family Residential",
    code: "R-1",
    type: "residential",
    color: "#10b981", // Emerald
    polygon: [
      [36.8550, -75.9850],
      [36.8590, -75.9810],
      [36.8560, -75.9730],
      [36.8510, -75.9780],
    ],
    description: "Max height 35ft, minimum rear setback 25ft.",
  },
  {
    id: "zone-b2",
    name: "B-2 Community Business & Mixed-Use District",
    code: "B-2",
    type: "commercial",
    color: "#f59e0b", // Amber
    polygon: [
      [36.8500, -75.9770],
      [36.8530, -75.9720],
      [36.8480, -75.9680],
      [36.8450, -75.9740],
    ],
    description: "Ground floor commercial with multi-family residential permitted.",
  },
];

const SAMPLE_MARKERS: ParcelMarker[] = [
  {
    id: "p-1",
    address: "450 North Elm St",
    parcelId: "Tax Map Parcel 104-55-A",
    coords: [36.8540, -75.9790],
    ordinanceId: "ORD-2026-102",
    page: 4,
    details: "Approved rear setback reduction from 25ft to 15ft.",
  },
  {
    id: "p-2",
    address: "782 South Oak Street",
    parcelId: "APN 88-12-004",
    coords: [36.8470, -75.9710],
    ordinanceId: "ORD-2026-74",
    page: 2,
    details: "Communications repeater tower conditional use permit.",
  },
];

function MapController({ center }: { center: [number, number] }) {
  const map = useMap();
  useEffect(() => {
    map.setView(center, 14);
  }, [center, map]);
  return null;
}

export default function ZoningMapViewer({
  zones = SAMPLE_ZONES,
  markers = SAMPLE_MARKERS,
  activeMarkerId,
  onSelectMarker,
}: ZoningMapViewerProps) {
  const defaultCenter: [number, number] = [36.8529, -75.9780];
  const activeMarker = markers.find((m) => m.id === activeMarkerId);
  const currentCenter = activeMarker ? activeMarker.coords : defaultCenter;

  return (
    <div className="zoning-map-viewer h-full w-full relative flex flex-col">
      {/* Legend Header */}
      <div className="absolute top-3 left-3 z-[1000] bg-card/90 backdrop-blur border border-border px-3 py-2 rounded-lg shadow-md text-xs flex items-center gap-3">
        <span className="font-semibold text-foreground">Zoning Boundaries:</span>
        <div className="flex items-center gap-1.5">
          <span className="h-2.5 w-2.5 rounded-full bg-emerald-500 inline-block" />
          <span className="text-[11px] text-muted-foreground">R-1 Residential</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="h-2.5 w-2.5 rounded-full bg-amber-500 inline-block" />
          <span className="text-[11px] text-muted-foreground">B-2 Commercial</span>
        </div>
      </div>

      <div className="flex-1 w-full h-full">
        <MapContainer
          center={defaultCenter}
          zoom={14}
          scrollWheelZoom={true}
          className="h-full w-full"
        >
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />
          <MapController center={currentCenter} />

          {/* Render Zoning Boundary Lines & Polygons */}
          {zones.map((zone) => (
            <React.Fragment key={zone.id}>
              <Polygon
                positions={zone.polygon}
                pathOptions={{
                  color: zone.color,
                  fillColor: zone.color,
                  fillOpacity: 0.18,
                  weight: 2,
                  dashArray: "4, 4",
                }}
              >
                <Popup>
                  <div className="p-1 space-y-1 text-xs">
                    <div className="font-bold" style={{ color: zone.color }}>{zone.name}</div>
                    <div className="text-[11px] text-muted-foreground">{zone.description}</div>
                  </div>
                </Popup>
              </Polygon>
            </React.Fragment>
          ))}

          {/* Render Parcel Pins */}
          {markers.map((marker) => (
            <Marker
              key={marker.id}
              position={marker.coords}
              icon={defaultIcon}
              eventHandlers={{
                click: () => {
                  if (onSelectMarker) onSelectMarker(marker);
                },
              }}
            >
              <Popup>
                <div className="p-1 space-y-1 text-xs max-w-[200px]">
                  <div className="font-bold text-primary">{marker.address}</div>
                  {marker.parcelId && <div className="text-[11px] font-mono text-muted-foreground">{marker.parcelId}</div>}
                  {marker.details && <div className="text-[11px] text-foreground">{marker.details}</div>}
                  <div className="text-[10px] text-primary font-medium pt-1">
                    Ordinance: {marker.ordinanceId || "N/A"} (Page {marker.page})
                  </div>
                </div>
              </Popup>
            </Marker>
          ))}
        </MapContainer>
      </div>
    </div>
  );
}
