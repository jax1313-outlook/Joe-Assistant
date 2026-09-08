# JOE Display Architecture v1.0

**Status:** LOCKED  
**Project:** JOE - Level 4 Operational Agent Interface  
**Parent System:** Dispatch  
**Authority:** Mike Zachary  
**Architecture Status:** Approved Baseline

---

# Mission

The JOE Display System is a Human Driver + Level 4 Agent operational workspace.

The purpose of the display system is to support mission execution, maintain operational awareness, reduce cognitive load, and provide immediate access to mission-critical information while preserving human authority.

The system is not:

- A chatbot
- A dashboard
- A trucking app
- A GPS application
- An entertainment system

The system is:

**A Human-Agent Mission Workstation**

---

# Human Driver + Level 4 Agent Doctrine

The JOE Display System represents a cooperative workspace between:

## Human Driver

Responsible for:

- Vehicle operation
- Safety
- Freight inspection
- Customer interaction
- Human judgment
- Final authority

## JOE (Level 4 Operational Agent)

Responsible for:

- Mission monitoring
- Information retrieval
- Information organization
- Communication support
- Facility intelligence
- Route intelligence
- Schedule monitoring
- Cognitive load reduction

Neither party operates independently.

The display serves as a shared operational environment where both driver and agent maintain awareness of the current mission.

---

# Design Goal

Reduce dependence on:

- Clipboards
- Printed load confirmations
- Handwritten notes
- Manual information searches
- Multiple disconnected applications

while preserving all legally required documentation.

## Documentation Doctrine

The display supplements but does not replace regulatory requirements.

### Door Pocket

Contains:

- Hazmat documentation
- Emergency response information
- Legally required reference materials

### Inspection Documentation Storage

Contains:

- Registration
- Insurance
- Permits
- DOT inspection materials

### Tablet Display

Contains:

- Operational information
- Route information
- Facility intelligence
- Load intelligence
- Mission information
- Joe interactions

---

# Shared Awareness Doctrine

The display shall continuously answer the following questions:

- What load am I working?
- What stop am I working?
- What time is it?
- What am I hauling?
- Where am I?
- Where am I on the mission?
- Am I on time?
- What is Joe telling me?
- Who controls this freight?
- What happens at this location?

---

# Interface Philosophy

The driver should be able to understand the current mission within seconds.

Information presentation must prioritize:

1. Current Mission
2. Current Stop
3. Current Status
4. Location Awareness
5. Operational Actions

The system shall not prioritize administrative functions over operational awareness.

---

# Card-Centric Architecture

Dispatch Card Doctrine remains the primary information architecture.

Cards are operational objects.

Cards are not decorative interface elements.

Cards provide progressive access to mission information.

---

# Progressive Detail Doctrine

## Level 1 Information

Visible immediately.

No interaction required.

Examples:

- Active stop
- Current time
- Pickup
- Delivery
- Mission status

---

## Level 2 Information

Single interaction required.

Tap to expand.

Examples:

- Shipper
- Commodity
- Stop information
- Load Control

---

## Level 3 Information

Operational detail.

Displayed only when requested.

Examples:

- Cargo placement diagrams
- Contact details
- Facility intelligence
- Commodity specifications

---

# Current Mission Screen

## Purpose

Primary travel screen.

Primary operations screen while vehicle is moving.

The Current Mission Screen answers:

- What load?
- What stop?
- What time?
- What commodity?
- What route?
- What facility?
- What status?
- What is Joe telling me?

---

# Current Mission Layout

## Header

### Left

```text
LEVEL 1 JOE
```

### Right

```text
ACTIVE STOP
CURRENT TIME
```

Current time remains permanently visible.

Appointment-driven freight operations require continuous time awareness.

---

# Left Information Column

Displays:

- Pickup
- Delivery
- Active Load Information

Purpose:

Mission orientation.

---

# Load Card Area

Default collapsed fields:

```text
SHIPPER
COMMODITY
AMOUNT
STOP
LOAD CONTROL
```

Each field is a button.

Each field expands and collapses.

---

# Expand / Collapse Doctrine

Standard behavior:

Tap = Expand

Tap Again = Collapse

No popup windows.

No menu trees.

No navigation loss.

Driver remains within mission context.

---

# Shipper Card

Collapsed:

```text
SHIPPER: ABC FREIGHT
```

Expanded:

Displays:

- Company
- Contact information
- Phone numbers
- Special instructions
- Operational notes

---

# Commodity Card

Collapsed:

```text
COMMODITY: MEDICAL SUPPLIES
```

Expanded:

Displays:

- Commodity description
- Special handling
- Hazmat information
- Securement requirements
- Temperature requirements

---

# Amount Card

Collapsed:

```text
AMOUNT: 14 PALLETS
```

Expanded:

Displays:

- Quantity
- Cargo layout
- Trailer representation
- Freight position
- Stop-specific freight allocation

Purpose:

Help the driver identify exactly which freight belongs to the active stop.

---

# Stop Card

Collapsed:

```text
STOP #2
```

Expanded:

Displays:

- Appointment information
- Dock assignments
- Facility instructions
- Delivery requirements
- Stop intelligence

---

# Load Control Doctrine

Load Control is a primary operational element.

Load Control is assigned at the stop level.

Not necessarily the broker.

May be:

- Broker
- Shipper
- Receiver
- Commodity Owner
- Level 1 Transport

Primary question answered:

```text
Who do I call?
```

Load Control identifies:

- Freight owner
- Operational controller
- Authority contact
- Claim contact
- Exception contact

Load Control may differ between stops.

---

# Route Progress Map

Purpose:

Mission position awareness.

Displays:

- Route
- Vehicle position
- Mission progress

Answers:

```text
Where am I on this mission?
```

Not intended as the primary navigation interface.

---

# Facility Intelligence Map

Purpose:

Facility approach awareness.

Priority:

1. Facility Map
2. Satellite View
3. Standard Map

Supports identification of:

- Truck entrances
- Gates
- Receiving offices
- Scale houses
- Security stations
- Dock locations

---

# Expandable Map Doctrine

Facility map supports:

```text
Tap → Expand

Tap → Contract
```

Expanded state occupies the full tablet.

Supports:

- Zoom
- Pan
- Inspection

Returns directly to mission view.

---

# Navigation Source Preference

Preferred navigation provider:

1. TruckMap
2. Alternative Truck-Safe Provider
3. Standard Navigation

Reason:

Truck-safe routing must take priority over shortest-path routing.

---

# Joe Communication Panel

Purpose:

Operational communications.

Not a chat window.

Not a transcript viewer.

Not conversation history.

Examples:

```text
Good Morning Mike.

Construction Delay Ahead.

Receiver Requests Dock 7.

Appointment Confirmed.
```

The panel displays what Joe is currently communicating to the driver.

---

# On-Time Status Doctrine

Complex calculations shall be compressed into operational status indicators.

Examples:

```text
ON TIME
```

```text
DELAYED
```

```text
AT RISK
```

The driver should not need to interpret multiple ETA calculations.

---

# Navigation Doctrine

A Next Stop control shall be present.

Purpose:

Advance mission context.

Behavior:

Selecting Next Stop loads the same Current Mission Screen architecture using the next stop's data.

Layout remains unchanged.

Mission context changes.

---

# Motion Doctrine

Motion exists only to support understanding.

Allowed:

- Expand
- Collapse
- Status transitions

Avoid:

- Decorative animations
- Excessive movement
- Entertainment effects
- Visual distractions

---

# Visual Language Doctrine

Target aesthetic:

**Professional Operations Workstation**

Not:

- Traditional trucking software
- Generic transportation dashboards
- Social media applications
- Consumer chat interfaces
- Sci-fi displays
- Gaming interfaces

Design characteristics:

- Calm
- Professional
- Modern
- Readable
- Mission-focused

---

# Architecture Status

LOCKED

This document defines:

WHY the system exists.

Subsequent specifications define:

WHAT the system contains.

---

# Next Document

```text
CURRENT_MISSION_SCREEN_SPEC_v1.md
```

Defines:

- Screen layout
- Buttons
- Fields
- Card actions
- Expansion behavior
- Data sources
- User interactions
- Screen-specific requirements