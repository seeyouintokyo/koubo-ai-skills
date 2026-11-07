import sys
from df.enhance import enhance, init_df, load_audio, save_audio
model, state, _ = init_df()
audio, _ = load_audio(sys.argv[1], sr=state.sr())
out = enhance(model, state, audio, atten_lim_db=float(sys.argv[3]) if len(sys.argv)>3 else None)
save_audio(sys.argv[2], out, state.sr())
print("saved", sys.argv[2], state.sr())
