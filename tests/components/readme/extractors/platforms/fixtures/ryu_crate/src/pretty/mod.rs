/// Unsafe function that mirrors the C implementation of Ryu.
pub unsafe fn format64(f: f64, result: *mut u8) -> usize {
    let _ = (f, result);
    0
}
