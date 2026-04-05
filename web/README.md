# SAMS Score Board Web

## Iframe Embed

Use `embed=1` to load the reduced UI inside an iframe.

Example URLs:

- `/competition/<competition-uuid>/teams?embed=1`
- `/competition/<competition-uuid>/plan?embed=1`
- `/competition/<competition-uuid>/live?embed=1`
- `/league/<league-uuid>/teams?embed=1`
- `/league/<league-uuid>/plan?embed=1`
- `/league/<league-uuid>/live?embed=1`

Example host page:

```html
<iframe
  id="score-board-frame"
  src="https://example.com/competition/123e4567-e89b-12d3-a456-426614174000/live?embed=1"
  style="width: 100%; height: 600px; border: 0;"
  loading="lazy"
></iframe>

<script>
  window.addEventListener("message", (event) => {
    if (event.data?.type !== "sams-score-board:window-size") {
      return;
    }

    console.log("iframe size", event.data.payload.width, event.data.payload.height);
  });
</script>
```

When embedded in an iframe, the app posts this message to the parent window on load and on resize:

```js
{
  type: "sams-score-board:window-size",
  payload: {
    width: 1024,
    height: 768
  }
}
```

For production usage, validate `event.origin` in the parent page before consuming the message.
