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

Text, SMS, and URL text support local keyword screening of 1–800 characters. Results show words matched in the current submission and the number of matching rule categories, not a fixed risk score or confidence. URLs are not visited or checked against reputation services. Rules cannot understand negation or context; no match does not mean safe. Input is neither uploaded nor persisted. Only matched keywords are passed to the result page through its event channel.

Screenshot OCR is not connected; submission is disabled with a text-input alternative. Q&A, training, statistics, and administration pages are explicitly marked as demonstrations. Online model conversations, training evaluation, and backend services remain unimplemented. General verification advice is predefined.

The current `pages/` code does not call `wx.request` or cloud functions. Therefore, its OCR, RAG Q&A, and report displays should not be interpreted as connected algorithms. User information, ability statistics, and administration displays do not constitute an implemented backend data system.

## Preview

1. Import the **repository root** into WeChat DevTools. `project.config.json` identifies the Mini Program project.
2. Configure the AppID to use. The repository defaults to `touristappid`, not an AppID for a published application.
3. Compile in a DevTools environment supporting Skyline to inspect the pages and navigation.

Previewing the current UI requires neither the Python project nor a Qwen API key. Publishing and backend integration require further implementation.

## Relationship to the RAG Project

Both projects share the campus anti-fraud theme and the recognition–explanation–training design approach, but they currently share no runtime, request API, or user data. The RAG engine could serve as the basis of a future backend integration; this is a development direction, not an existing capability.

## Maintenance and Regression Checks

The recognition flow prevents repeated taps and clears pending navigation when the page is hidden, unloaded, or its input mode changes. Invalid launch modes fall back to text. Recognition remains a prototype demonstration; these changes do not connect it to RAG.

Requires Node.js 18 or newer, with no npm dependencies:

```sh
node --test tests/*.test.cjs
```

Covers input limits, dynamic results, exclusion of submitted sensitive values from results, repeated submissions, hide/unload cancellation, navigation retry, empty results, tab navigation, and source completeness. Skyline compilation, WeUI layout, keyboards, and device navigation still require WeChat DevTools/device verification. Node tests do not replace host-runtime validation.
