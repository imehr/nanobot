# Capture Window Fixed Action Bar Design

**Goal:** Keep the main `Capture to Nanobot` action visible as soon as the macOS app window opens, without requiring the user to scroll.

## Problem

The current capture window renders the entire form in one vertical stack. On shorter window heights, the primary capture button can end up below the fold. That makes the first-use experience feel broken because the user can fill content but cannot immediately see how to submit it.

## Recommended Approach

Use a split layout:

- the form body remains in a vertical `ScrollView`
- the status text and `Capture to Nanobot` button move into a fixed bottom action bar
- the result card stays in the scrollable content area

This keeps the primary action anchored while preserving flexible space for long notes, attachments, and capture results.

## UX Rules

- The window should open with the capture button visible at the bottom.
- The action bar should remain visible while the user scrolls the form.
- The result card should not be pinned; it should remain part of the main content flow.
- The text editor height should be slightly reduced so more of the form fits in the initial viewport.

## Verification

- Add a regression test that checks the view source for a fixed bottom action bar pattern and a scrollable content container.
- Rebuild and reinstall the app locally.
- Launch the installed app and verify the button is visible on open.
