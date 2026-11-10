# Project 1: Anti-Fraud Coach WeChat Mini Program

[中文](mini-program.md) | [English](mini-program.en.md)

[Repository overview](../README.en.md)

## Purpose

A UI and interaction prototype of an anti-fraud coach for university students. It demonstrates the journey from risk recognition to explanations and advice, Q&A, scenario training, and ability reports, alongside administration screens.

## Technology and Directories

Built with JavaScript, WXML, WXSS, the WeChat Mini Program Skyline renderer, and the glass-easel component framework.

- `app.js`, `app.json`, `app.wxss`: application entry point, page registration, and global styles.
- `pages/`: home, recognition, results, Q&A, training, reports, profile, and administration pages.
- `components/`: branding components.
- `assets/`, `styles/`: icons, illustrations, and visual styles.
- `utils/`: routing and tab navigation helpers.
- `project.config.json`: WeChat DevTools configuration.

## Existing Behavior and Implementation Boundaries

The screens include recognition entry points for text, screenshot OCR, links, and SMS, alongside risk signals, suggested actions, and training scenarios. These are currently UI demonstrations: the recognition button navigates to the results page after a timer, while result labels and advice are predefined. The Q&A and training pages do not implement online model conversations or a complete training evaluation service.

The current `pages/` code does not call `wx.request` or cloud functions. Therefore, its OCR, RAG Q&A, and report displays should not be interpreted as connected algorithms. User information, ability statistics, and administration displays do not constitute an implemented backend data system.

## Preview

1. Import the **repository root** into WeChat DevTools. `project.config.json` identifies the Mini Program project.
2. Configure the AppID to use. The repository defaults to `touristappid`, not an AppID for a published application.
3. Compile in a DevTools environment supporting Skyline to inspect the pages and navigation.

Previewing the current UI requires neither the Python project nor a Qwen API key. Publishing and backend integration require further implementation.

## Relationship to the RAG Project

Both projects share the campus anti-fraud theme and the recognition–explanation–training design approach, but they currently share no runtime, request API, or user data. The RAG engine could serve as the basis of a future backend integration; this is a development direction, not an existing capability.
