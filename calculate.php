<?php

/**************CHANGE CURRENT GAME WEEK BEFORE RUNNING************************/

//current GW
$currentGW = 16;

//threshold
$threshold = 5;

//#teamABS members: Holla, Kutty, Chandak, Hannibal
$teamABS = ['Sardaukar' => '1139641',
			'Pointus Maximus' => '954786',
			'Vetti Dogs' => '4113',
			'FCSvenska' => '947222',
			];
//#teamSam = evil members: Samarth, Suzie, MH, Parjun (check him out at betparjun.com - and also in local bars in Bangalore)
$teamSam = ['Playmakers' => '594887',
			'Swalpa adjust maadi' => '374413',
			'The unsullied' => '2276264',
			'HowToScoreGoalsXI' => '992491',
			];

//init points
$teamABSPoints = [];
$teamSamPoints = [];

//calculate totals
//#teamABS
echo "\nRetrieving data for #teamABS:\n";
$teamABSTotal = retrievePageAndCalculateTotals($teamABS, $teamABSPoints, $currentGW);

//#teamSam
echo "\nRetrieving data for #teamSam:\n";
$teamSamTotal = retrievePageAndCalculateTotals($teamSam, $teamSamPoints, $currentGW);

//calculate week's average
//#teamABS
echo "\nCalculating average for #teamABS:\n";
$teamABSAverage = getAverage($teamABSPoints, $teamABSTotal, $threshold);
echo "#teamABS average this week: " . $teamABSAverage . "\n";

//#teamSam
echo "\nCalculating average for #teamSam:\n";
$teamSamAverage = getAverage($teamSamPoints, $teamSamTotal, $threshold);
echo "#teamSam average this week: " . $teamSamAverage . "\n";

//retrieve current points tally
$file = "pointsTracker.json";
$pointsTally = json_decode(file_get_contents($file), true);

//add calculated averages
$pointsTally['#teamABS'] += $teamABSAverage;
$pointsTally['#teamSam'] += $teamSamAverage;

//print
echo "\nChampionship Details:\n";
echo "#teamABS championship total: " . $pointsTally['#teamABS'] . "\n";
echo "#teamSam championship total: " . $pointsTally['#teamSam'] . "\n";

//write back
file_put_contents($file, json_encode($pointsTally));

//done!

function retrievePageAndCalculateTotals($teamMembers, &$teamPoints, $currentGW) {
	// create curl resource 
	$ch = curl_init(); 
	//init total
	$total = 0;
	//iterate over each member 
	foreach ($teamMembers as $name => $id) {
		echo "Extracting points for " . $name . "... ";
		//build the URL to retrieve points
		$personalURL = "/entry/" . $id . "/history/";
		$pointsURL = "http://fantasy.premierleague.com" . $personalURL;
		// set url 
	    curl_setopt($ch, CURLOPT_URL, $pointsURL); 
	    //return the transfer as a string 
	    curl_setopt($ch, CURLOPT_RETURNTRANSFER, 1); 
	    // $pageHTML contains the html source 
	    $pageHTML = curl_exec($ch); 

	    //extract points of current gameweek
	    $pattern = "@<td class=\"ismCol2\">(.*)</td>@i";

	    //$pattern = "@<a href=\"" . $patternURL . "\">(.*)</a></td>@";
    	preg_match_all($pattern, $pageHTML, $matches);

	   	//pick up the matches
	   	$allMatches = $matches[1];

	    //record points
	    $teamPoints[$name] = intval($allMatches[$currentGW - 1]);

	    //print points
	   	echo $teamPoints[$name] . "\n";

	    //add to total
	    $total += $teamPoints[$name];
	}

	// close curl resource to free up system resources 
	curl_close($ch); 

	//return total
	return $total;
}


function getAverage($teamPoints, $total, $threshold) {
	//calculate average without pruning
	$noOfMembers = count($teamPoints);
	if ($noOfMembers == 0) {
		echo "No members in team!" . "\n";
		return 0;
	}
	$teamAverage = $total / $noOfMembers;

	//find min
	$minName = min(array_keys($teamPoints, min($teamPoints)));
	$minPoints = $teamPoints[$minName];

	//prune if lower than threshold compared to average
	if ($minPoints <= $teamAverage - $threshold) {
		//print
		echo $minName . "'s points were pruned out. Points: " . $minPoints ." Average: " . $teamAverage . " Threshold: " . $threshold . "\n";
		
		//reduce no of members
		$noOfMembers--;
		
		//reduce total by minpoints
		$total = $total - $minPoints;
	}

	//return average
	return $total / $noOfMembers;
}
?>