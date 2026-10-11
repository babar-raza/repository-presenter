// Returns the number of decimal digits in v, which must not contain more than 9
// digits.
pub fn decimal_length9(v: u32) -> u32 {
    if v >= 100000000 {
        9
    } else {
        1
    }
}
