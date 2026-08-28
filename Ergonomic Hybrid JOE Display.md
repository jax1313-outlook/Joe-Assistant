## Building the Ergonomic Hybrid: JOE Display Architecture meet Luxury Design
You are merging two powerful, non-traditional philosophies. On one hand, you have an ultra-premium luxury digital aesthetic (Onyx surfaces, Brushed Platinum typography, and Champagne Gold accents). On the other, you have a highly rigid, battle-tested operational cockpit—the JOE Display Architecture—which treats the display as an in-cab mission workstation shared between a Human Driver and a Level 4 Autonomous AI Agent.
The Driver Portal must not feel like a typical app. It is a shared operational workspace where the human has final authority and JOE manages info retrieval, status monitoring, and route intelligence.
Let's design a high-priority dashboard component for the Driver Portal: the Unified Active Mission Workspace.
This component perfectly executes your luxury visual token configuration while remaining true to the strict Load Card Doctrine, Load Control Doctrine, On-Time Status Doctrine, and Dual-Map Architecture required for real-world operations.
------------------------------
## 🚛 3. Unified Active Mission Workspace (Driver Portal)
Create this file at components/driver-mission-workspace.tsx in your framework structure:

"use client";
import React, { useState } from "react";import { motion, AnimatePresence } from "framer-motion";import { 
  Shield, 
  MapPin, 
  Box, 
  Layers, 
  Phone, 
  Maximize2, 
  Minimize2, 
  Compass, 
  AlertCircle 
} from "lucide-react";
// Types matching the JOE Display Architecture Contexttype CardSection = "shipper" | "commodity" | "amount" | "stop" | "load_control";
interface LoadData {
  manifestId: string;
  onTimeStatus: "ON TIME" | "AT RISK" | "DELAYED";
  eta: string;
  shipper: { name: string; location: string; details: string };
  commodity: { type: string; hazardClass: string; handling: string };
  amount: { weight: string; pallets: number; volume: string };
  stop: { type: string; sequence: string; address: string; window: string };
  loadControl: { pocName: string; role: string; phone: string; authority: string };
}
export default function DriverMissionWorkspace() {
  // Shared Operational Workspace State
  const [expandedCard, setExpandedCard] = useState<CardSection | null>("shipper");
  const [isFullscreenMap, setIsFullscreenMap] = useState<boolean>(false);

  const missionData: LoadData = {
    manifestId: "MANIFEST // JOE-L4-9902X",
    onTimeStatus: "ON TIME",
    eta: "16:30 MST (In 1hr 42min)",
    shipper: {
      name: "Vanguard Aero Systems",
      location: "Node Facility Alpha (Phoenix, AZ)",
      details: "Secure gate entry 4. High-value dock assignment tier-1.",
    },
    commodity: {
      type: "Carbon Matrix Flight Assemblies",
      hazardClass: "Class 9 // High-Value Structural",
      handling: "Pre-conditioned transport climate matrix required.",
    },
    amount: {
      weight: "32,450 lbs",
      pallets: 18,
      volume: "3,200 cu ft",
    },
    stop: {
      type: "Consignee Delivery Point",
      sequence: "Stop 02 of 02",
      address: "8800 Sky Harbor Logistics Blvd, Suite X",
      window: "Firm Appointment: 16:00 - 17:30 MST",
    },
    loadControl: {
      pocName: "Marcus Vance",
      role: "Logistics Commander (Control Desk Terminal 4)",
      phone: "+1 (800) 555-0190",
      authority: "Authorized for structural route deviations and terminal seal bypass.",
    },
  };

  const toggleCard = (section: CardSection) => {
    setExpandedCard(expandedCard === section ? null : section);
  };

  return (
    <div className="w-full min-h-screen bg-[#0D0D0E] text-[#E5E5E5] font-sans antialiased p-4 md:p-6 lg:p-8">
      
      {/* HUD Mission Context Header */}
      <div className="w-full border-b border-[#1D1D20] pb-6 mb-6 flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <div className="flex items-center gap-3">
            <span className="text-[10px] uppercase tracking-[0.25em] text-[#D4AF37] font-semibold">Active Human-Agent Workstation</span>
            <div className="flex items-center gap-1.5 px-2 py-0.5 bg-neutral-900 border border-neutral-800 rounded-sm">
              <Shield className="w-3 h-3 text-[#D4AF37]" />
              <span className="text-[9px] font-mono tracking-wider text-neutral-400">JOE L4 CONNECTED</span>
            </div>
          </div>
          <h1 className="text-xl md:text-2xl font-light tracking-tight mt-1 text-white font-serif">
            {missionData.manifestId}
          </h1>
        </div>

        {/* Operational Status Panel - Pure Operational Answers Only */}
        <div className="flex gap-4 items-center bg-[#141416] border border-[#1D1D20] p-4 rounded-none min-w-[280px]">
          <div className="flex-1">
            <span className="text-[10px] uppercase tracking-wider text-[#8A8A93] block">Mission Position State</span>
            <span className="text-xs font-mono font-medium text-white block mt-0.5">{missionData.eta}</span>
          </div>
          <div className="text-right">
            <span className="text-[10px] uppercase tracking-wider text-[#8A8A93] block">Status Matrix</span>
            <span className="inline-block mt-0.5 text-xs font-mono font-bold tracking-widest text-emerald-400">
              {missionData.onTimeStatus}
            </span>
          </div>
        </div>
      </div>

      {/* Primary Split Viewport Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        
        {/* Left Hand: Load Card Architecture (5 Columns) */}
        <div className="lg:col-span-5 space-y-3">
          <div className="pb-2 border-b border-[#1D1D20]">
            <h2 className="text-[11px] uppercase tracking-[0.2em] text-[#8A8A93] font-semibold">
              Mission Ledger & Manifest Controls
            </h2>
          </div>

          {/* 1. Shipper Card */}
          <LoadCard 
            title="Shipper Origin" 
            summary={missionData.shipper.name}
            isOpen={expandedCard === "shipper"}
            onClick={() => toggleCard("shipper")}
          >
            <div className="space-y-2 text-xs">
              <div>
                <span className="text-[#8A8A93] uppercase block text-[9px] tracking-wider">Facility Hub</span>
                <p className="text-white font-medium mt-0.5">{missionData.shipper.location}</p>
              </div>
              <div>
                <span className="text-[#8A8A93] uppercase block text-[9px] tracking-wider">JOE Agent Briefing</span>
                <p className="text-neutral-400 font-light mt-0.5 leading-relaxed">{missionData.shipper.details}</p>
              </div>
            </div>
          </LoadCard>

          {/* 2. Commodity Card */}
          <LoadCard 
            title="Commodity Architecture" 
            summary={missionData.commodity.type}
            isOpen={expandedCard === "commodity"}
            onClick={() => toggleCard("commodity")}
          >
            <div className="space-y-2 text-xs">
              <div>
                <span className="text-[#8A8A93] uppercase block text-[9px] tracking-wider">Classification Group</span>
                <p className="text-white font-medium mt-0.5">{missionData.commodity.hazardClass}</p>
              </div>
              <div>
                <span className="text-[#8A8A93] uppercase block text-[9px] tracking-wider">Operational Protocols</span>
                <p className="text-neutral-400 font-light mt-0.5 leading-relaxed">{missionData.commodity.handling}</p>
              </div>
            </div>
          </LoadCard>

          {/* 3. Amount Card */}
          <LoadCard 
            title="Cargo Allocation Payload" 
            summary={`${missionData.amount.weight} // ${missionData.amount.pallets} Units`}
            isOpen={expandedCard === "amount"}
            onClick={() => toggleCard("amount")}
          >
            <div className="grid grid-cols-3 gap-4 text-xs">
              <div>
                <span className="text-[#8A8A93] uppercase block text-[9px] tracking-wider">Gross Weight</span>
                <p className="text-white font-mono mt-0.5">{missionData.amount.weight}</p>
              </div>
              <div>
                <span className="text-[#8A8A93] uppercase block text-[9px] tracking-wider">Asset Units</span>
                <p className="text-white font-mono mt-0.5">{missionData.amount.pallets} Pallets</p>
              </div>
              <div>
                <span className="text-[#8A8A93] uppercase block text-[9px] tracking-wider">Cube Capacity</span>
                <p className="text-white font-mono mt-0.5">{missionData.amount.volume}</p>
              </div>
            </div>
          </LoadCard>

          {/* 4. Stop Card */}
          <LoadCard 
            title="Target Stop Objective" 
            summary={missionData.stop.sequence}
            isOpen={expandedCard === "stop"}
            onClick={() => toggleCard("stop")}
          >
            <div className="space-y-2 text-xs">
              <div className="flex items-start gap-2">
                <MapPin className="w-4 h-4 text-[#D4AF37] mt-0.5 shrink-0" />
                <div>
                  <span className="text-[#8A8A93] uppercase block text-[9px] tracking-wider">{missionData.stop.type}</span>
                  <p className="text-white font-medium mt-0.5">{missionData.stop.address}</p>
                </div>
              </div>
              <div className="bg-[#0D0D0E] p-3 border border-[#1D1D20]">
                <span className="text-[#D4AF37] uppercase block text-[9px] tracking-wider font-semibold">Temporal Window Constraint</span>
                <p className="text-neutral-200 font-mono mt-0.5">{missionData.stop.window}</p>
              </div>
            </div>
          </LoadCard>

          {/* 5. Load Control Card (Doctrine: Operational Point of Contact) */}
          <LoadCard 
            title="Load Control Desk" 
            summary={missionData.loadControl.pocName}
            isOpen={expandedCard === "load_control"}
            onClick={() => toggleCard("load_control")}
            isHighlight={true}
          >
            <div className="space-y-3 text-xs">
              <div className="flex justify-between items-start">
                <div>
                  <span className="text-[#8A8A93] uppercase block text-[9px] tracking-wider">Command Authority</span>
                  <p className="text-white font-medium mt-0.5">{missionData.loadControl.role}</p>
                  <p className="text-neutral-400 font-light mt-1 text-[11px] leading-relaxed">
                    {missionData.loadControl.authority}
                  </p>
                </div>
                
                <a 
                  href={`tel:${missionData.loadControl.phone}`}
                  className="flex items-center gap-1.5 px-3 py-2 bg-white text-black font-semibold text-[10px] tracking-wider uppercase transition-colors hover:bg-neutral-200"
                >
                  <Phone className="w-3 h-3" />
                  Call Node
                </a>
              </div>
            </div>
          </LoadCard>
        </div>

{/* Right Hand: Dual-Map Tactical Workspaces (7 Columns) */}
<div className={lg:col-span-7 space-y-6 transition-all duration-500 ${isFullscreenMap ? "absolute inset-0 z-50 bg-[#0D0D0E] p-6 lg:p-8" : ""}}>
{isFullscreenMap ? "Facility Approach Intelligence Map (Expanded)" : "Dual Route & Facility Intelligence Screens"}

<button
onClick={() => setIsFullscreenMap(!isFullscreenMap)}
className="text-[#8A8A93] hover:text-white transition-colors"
title={isFullscreenMap ? "Contract Workspace" : "Expand Facility Approach View"}
>
{isFullscreenMap ? : }

<div className={grid gap-4 ${isFullscreenMap ? "grid-cols-1 h-[calc(100vh-140px)]" : "grid-cols-1 md:grid-cols-2"}}>
{/* Screen Alpha: Route Progress Map (Always Standard Size) */}
{!isFullscreenMap && (


SCREEN 01 // ROUTE PROGRESS AWARENESS

I-40 W Corridor Corridor
POS ACTIVE

{/* Abstract Vector Graphic Layer */}






LAT: 35.1982° N
LON: 111.6513° W


)}
{/* Screen Beta: Facility Intelligence Map (Taps trigger scale shifts per Doctrine) */}
<div
onClick={() => !isFullscreenMap && setIsFullscreenMap(true)}
className={bg-[#141416] border transition-all duration-300 relative flex flex-col justify-between p-4 overflow-hidden ${ isFullscreenMap ? "h-full border-[#D4AF37]" : "h-[380px] border-[#1D1D20] cursor-pointer hover:border-neutral-700" }}
>


SCREEN 02 // FACILITY APPROACH INTEL
Sky Harbor Logistics Complex Perimeter

{!isFullscreenMap && }
{/* Mock Blueprint High-Value Facility Radar Layout */}






JOE Automated Gate Instructions


Approach via outer Lane 3. Optical RFID sensor will scan tractor plate automatically. Proceed directly along transit path line to Gate Structure Delta.


);
}
/* --- Internal Modular Sub-Components --- */
interface CardProps {
title: string;
summary: string;
isOpen: boolean;
onClick: () => void;
children: React.ReactNode;
isHighlight?: boolean;
}
function LoadCard({ title, summary, isOpen, onClick, children, isHighlight = false }: CardProps) {
return (
<div
className={border transition-all duration-300 select-none ${ isOpen ? "bg-[#141416] border-neutral-700 shadow-xl" : isHighlight ? "bg-[#141416] border-[#D4AF37]/40 hover:border-[#D4AF37]" : "bg-[#141416]/50 border-[#1D1D20] hover:border-neutral-800" }}
>
{/* Header Bar Trigger */}


<span className={text-[9px] uppercase tracking-[0.2em] block font-medium ${isHighlight ? "text-[#D4AF37]" : "text-[#8A8A93]"}}>
{title}


{summary}



{isOpen ? "[ CLOSE ]" : "[ OPEN ]"}

{/* Expandable Core Interface Walled Content Block */}

{isOpen && (
<motion.div
initial={{ height: 0, opacity: 0 }}
animate={{ height: "auto", opacity: 1 }}
exit={{ height: 0, opacity: 0 }}
transition={{ duration: 0.2, ease: "easeInOut" }}
className="overflow-hidden"
>


{children}


</motion.div>
)}


);
}


---

### 🎨 The Architectural Integration Blueprint

When you route your code generation tasks via **Claude Code** or **Jules**, understand how these components fuse into a system that does not look like standard industrial software:

1. **The Client Access Switchboard**: The login configuration file provided in your architecture documentation (`/src/app/auth/login/page.tsx`) acts as an elegant barrier gate. Passing a validated driver ID routes the terminal framework into the mobile-responsive `/portal/driver` environment.
2. **System Contrast**: By relying exclusively on typography sizing variables (`font-serif` mixed with monospace digits) and avoiding clunky table borders, the dashboard reads like a private aviation log or premium luxury platform while processing intense real-world telemetry.

<FollowUp>
Would you like me to construct the matching **API Routing Handlers** that Claude Code can use to bind this active mission view directly to a live fleet database stream?
</FollowUp>


