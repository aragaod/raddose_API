from beamline import redis
import json
import numpy
import pandas as pd


class flux_bs_lookup(object):
    def __init__(self, list_of_redis_keys):
        self.df = self.setup_df(list_of_redis_keys)
        self.slices_dfs = self.slice_beamsizes(self.df)
        self.models = self.polinomial_fit(degree=4)

    def setup_df(self, keys):
        payload = []
        for key in keys:
            payload.append(self.download_data_to_df(key))
        df = pd.concat(payload)
        return df

    def download_data_to_df(self, key):
        payload = json.loads(redis.get(key))
        print(f"Loaded {len(payload)} data entries for {key}")
        df = pd.DataFrame(payload)

        new_columns = [
            "energy",
            "beamsize.VAL",
            "beamsize.RBV",
            "n_lenses",
            "ringCurrent",
            "flux_density",
            "flux",
            "normalised_flux",
            "dcm_pitch",
            "dcm_roll",
            "fswt_dw_x",
            "fswt_dw_y",
            "human_time",
            "epoch",
        ]
        df = df.assign(normalised_flux=df["flux"] / df["ringCurrent"] * 300)
        df = df[new_columns]

        df = (
            df["beamsize.VAL"]
            .apply(pd.Series)
            .merge(df, left_index=True, right_index=True)
        )
        df.rename({0: "hzise_SP", 1: "vsize_SP"}, axis="columns", inplace=True)

        df = (
            df["beamsize.RBV"]
            .apply(pd.Series)
            .merge(df, left_index=True, right_index=True)
        )
        df.rename({0: "hzise_RBV", 1: "vsize_RBV"}, axis="columns", inplace=True)

        df.drop(["beamsize.VAL"], axis=1, inplace=True)

        df["Area"] = df["beamsize.RBV"].apply(numpy.prod)
        df["norm_flux_density"] = df["normalised_flux"] / df["Area"]
        df.drop(["beamsize.RBV"], axis=1, inplace=True)

        return df

    def slice_beamsizes(self, df):
        five = df[df["vsize_SP"] == 5.0]
        ten = df[df["vsize_SP"] == 10.0]
        fifteen = df[df["vsize_SP"] == 15.0]
        twenty = df[df["vsize_SP"] == 20.0]
        thirty = df[df["vsize_SP"] == 30.0]
        fourty = df[df["vsize_SP"] == 40.0]
        fifty = df[df["vsize_SP"] == 50.0]
        seventyfive = df[df["vsize_SP"] == 75.0]
        hundred = df[df["vsize_SP"] == 100.0]
        return {
            "5": five,
            "10": ten,
            "15": fifteen,
            "20": twenty,
            "30": thirty,
            "40": fourty,
            "50": fifty,
            "75": seventyfive,
            "100": hundred,
        }

    def polinomial_fit(self, degree=4):
        models = {}
        for key in self.slices_dfs:
            models[key] = numpy.poly1d(
                numpy.polyfit(
                    self.slices_dfs[key].energy, self.slices_dfs[key].normalised_flux, 4
                )
            )
        return models

    def calculate_flux(self, energy, v_size_sp):
        key = str(v_size_sp)

        if key in self.models.keys():
            return self.models[key](energy)
        else:
            print("Data for that beamsize is unavailable")
            return False

    def calc_filters(self, vertical, energy_eV):
        """f =(k*E^2)/N, N=(k*E^2)/f, k=55/(f+200) where f is vertical beam dimension"""
        # 	k = 55.055 / (vertical + 198.0)
        E = energy_eV / 1000.0
        k = 53.85 / (vertical + 198.0)
        N = k * (E ** 2)
        filters = round(N)
        return int(filters)

    def calc_beamsize_from_lenses(self, filters, energy_eV):
        """Reversing calc_filters function to calculate vertical size from number of lenses"""
        E = energy_eV / 1000.0
        k = filters / (E ** 2)
        vertical = 53.85 / k - 198.0
        horizontal = self.calc_horizontal(vertical, energy_eV)
        return (round(horizontal, 1), round(vertical, 1))

    def calc_horizontal(self, vertical, energy_eV):
        # TODO horizontal:vertical ratio energy dependent?
        ratio = 3.285 * (vertical ** -0.243)
        return ratio * vertical
