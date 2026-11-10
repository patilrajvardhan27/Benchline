import { linearScale, linePath, niceTicks, stepPath } from "./chartMath";

describe("linearScale", () => {
  it("maps the domain onto the range", () => {
    const s = linearScale([0, 10], [100, 200]);
    expect(s(0)).toBe(100);
    expect(s(5)).toBe(150);
    expect(s(10)).toBe(200);
  });
  it("supports inverted ranges for SVG y axes", () => {
    expect(linearScale([0, 1], [100, 0])(0.25)).toBe(75);
  });
  it("returns the middle when the domain has no width", () => {
    expect(linearScale([5, 5], [0, 10])(5)).toBe(5);
  });
});

describe("niceTicks", () => {
  it("picks round values inside the range", () => {
    expect(niceTicks(0, 1, 4)).toEqual([0, 0.2, 0.4, 0.6, 0.8, 1]);
    expect(niceTicks(0.021, 0.049, 4).every((t) => t >= 0.021 && t <= 0.049)).toBe(true);
  });
  it("handles a flat range", () => {
    expect(niceTicks(3, 3)).toEqual([3]);
  });
});

describe("paths", () => {
  it("holds the value until the next point in a step path", () => {
    expect(stepPath([{ x: 0, y: 10 }, { x: 5, y: 20 }])).toBe("M0,10 L5,10 L5,20");
  });
  it("extends the last value to the end of the chart", () => {
    expect(stepPath([{ x: 0, y: 10 }], 8)).toBe("M0,10 L8,10");
  });
  it("draws straight segments for a line path", () => {
    expect(linePath([{ x: 0, y: 1 }, { x: 2, y: 3 }])).toBe("M0,1 L2,3");
  });
  it("returns an empty path for no points", () => {
    expect(stepPath([])).toBe("");
  });
});
