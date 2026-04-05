import { render, screen } from "@testing-library/react";

import App from "./App";

describe("App", () => {
  it("renders auth page by default", () => {
    window.localStorage.clear();
    window.history.replaceState({}, "", "/login");

    render(<App />);

    expect(screen.getByRole("heading", { name: "把当前项目变成一个能实际操作的网站" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "进入网站" })).toBeInTheDocument();
  });
});
