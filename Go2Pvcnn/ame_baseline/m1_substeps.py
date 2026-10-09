"""Read-only diagnostic observer around the existing scene update hook."""


def observe_substeps(scene, step, read):
    original=scene.update
    samples=[]
    def observed_update(*args,**kwargs):
        result=original(*args,**kwargs)
        samples.append(read())
        return result
    scene.update=observed_update
    try:
        return step(),samples
    finally:
        scene.update=original
