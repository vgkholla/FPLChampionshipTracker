<?php

$pointsTally = [ '#teamABS'	=> 	0,
				 '#teamSam'	=>	0,
				];

$file = "pointsTracker.json";
file_put_contents($file, json_encode($pointsTally));