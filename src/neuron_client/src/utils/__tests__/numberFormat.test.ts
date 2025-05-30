import { formatNumber } from "../numberFormat";

describe("formatNumber", () => {
  describe("with default precision", () => {
    it("should return the number as string for numbers less than 1000", () => {
      expect(formatNumber(0)).toBe("0");
      expect(formatNumber(1)).toBe("1");
      expect(formatNumber(10)).toBe("10");
      expect(formatNumber(100)).toBe("100");
      expect(formatNumber(999)).toBe("999");
    });

    it("should format thousands with 'k' suffix", () => {
      expect(formatNumber(1000)).toBe("1.0k");
      expect(formatNumber(1500)).toBe("1.5k");
      expect(formatNumber(1999)).toBe("2.0k");
      expect(formatNumber(10000)).toBe("10.0k");
      expect(formatNumber(100000)).toBe("100.0k");
      expect(formatNumber(999999)).toBe("1000.0k");
    });

    it("should format millions with 'm' suffix", () => {
      expect(formatNumber(1000000)).toBe("1.0m");
      expect(formatNumber(1500000)).toBe("1.5m");
      expect(formatNumber(10000000)).toBe("10.0m");
      expect(formatNumber(100000000)).toBe("100.0m");
      expect(formatNumber(1234567890)).toBe("1234.6m");
    });

    it("should handle negative numbers with proper formatting", () => {
      expect(formatNumber(-1)).toBe("-1");
      expect(formatNumber(-999)).toBe("-999");
      expect(formatNumber(-1000)).toBe("-1.0k");
      expect(formatNumber(-1500)).toBe("-1.5k");
      expect(formatNumber(-1000000)).toBe("-1.0m");
      expect(formatNumber(-1500000)).toBe("-1.5m");
    });

    it("should handle decimal numbers correctly", () => {
      expect(formatNumber(0.5)).toBe("0.5");
      expect(formatNumber(999.99)).toBe("999.99");
      expect(formatNumber(1234.56)).toBe("1.2k");
      expect(formatNumber(1999.99)).toBe("2.0k");
      expect(formatNumber(1234567.89)).toBe("1.2m");
    });
  });

  describe("with custom precision", () => {
    it("should respect precision for numbers less than 1000", () => {
      expect(formatNumber(123.456, 0)).toBe("123.456");
      expect(formatNumber(123.456, 2)).toBe("123.456");
      expect(formatNumber(123.456, 3)).toBe("123.456");
    });

    it("should respect precision for thousands", () => {
      expect(formatNumber(1234, 0)).toBe("1k");
      expect(formatNumber(1234, 1)).toBe("1.2k");
      expect(formatNumber(1234, 2)).toBe("1.23k");
      expect(formatNumber(1234, 3)).toBe("1.234k");
      expect(formatNumber(1567, 0)).toBe("2k");
      expect(formatNumber(1567, 1)).toBe("1.6k");
      expect(formatNumber(1567, 2)).toBe("1.57k");
    });

    it("should respect precision for millions", () => {
      expect(formatNumber(1234567, 0)).toBe("1m");
      expect(formatNumber(1234567, 1)).toBe("1.2m");
      expect(formatNumber(1234567, 2)).toBe("1.23m");
      expect(formatNumber(1234567, 3)).toBe("1.235m");
      expect(formatNumber(1567890, 0)).toBe("2m");
      expect(formatNumber(1567890, 1)).toBe("1.6m");
      expect(formatNumber(1567890, 2)).toBe("1.57m");
    });

    it("should respect precision for negative numbers", () => {
      expect(formatNumber(-1234, 0)).toBe("-1k");
      expect(formatNumber(-1234, 1)).toBe("-1.2k");
      expect(formatNumber(-1234, 2)).toBe("-1.23k");
      expect(formatNumber(-1234567, 0)).toBe("-1m");
      expect(formatNumber(-1234567, 1)).toBe("-1.2m");
      expect(formatNumber(-1234567, 2)).toBe("-1.23m");
    });
  });

  describe("edge cases", () => {
    it("should handle exactly 1000", () => {
      expect(formatNumber(1000)).toBe("1.0k");
    });

    it("should handle exactly 1000000", () => {
      expect(formatNumber(1000000)).toBe("1.0m");
    });

    it("should handle zero", () => {
      expect(formatNumber(0)).toBe("0");
      expect(formatNumber(0, 0)).toBe("0");
      expect(formatNumber(0, 5)).toBe("0");
    });

    it("should handle very large numbers", () => {
      expect(formatNumber(Number.MAX_SAFE_INTEGER)).toBe("9007199254.7m");
      expect(formatNumber(Number.MAX_SAFE_INTEGER, 0)).toBe("9007199255m");
      expect(formatNumber(Number.MAX_SAFE_INTEGER, 3)).toBe("9007199254.741m");
    });

    it("should handle very small positive numbers", () => {
      expect(formatNumber(0.001)).toBe("0.001");
      expect(formatNumber(Number.MIN_VALUE)).toBe("5e-324");
    });

    it("should handle Infinity without suffix", () => {
      expect(formatNumber(Infinity)).toBe("Infinity");
      expect(formatNumber(-Infinity)).toBe("-Infinity");
    });

    it("should handle NaN", () => {
      expect(formatNumber(NaN)).toBe("NaN");
    });

    it("should handle negative edge cases", () => {
      expect(formatNumber(-1000)).toBe("-1.0k");
      expect(formatNumber(-1000000)).toBe("-1.0m");
      expect(formatNumber(-999)).toBe("-999");
      expect(formatNumber(-999999)).toBe("-1000.0k");
    });
  });
});
